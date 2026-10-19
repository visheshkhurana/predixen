// /survival/:id share pages: answer a real 404 when the simulation does not
// exist. Existence comes from the FastAPI backend (GET
// /survival-sim/results/{id} — Express strips /api before proxying), with a
// short timeout and a small in-process cache. Any backend failure (timeout,
// 5xx, network) returns "unknown" and the caller keeps the old behaviour:
// 200 + noindex shell.
import { renderHtmlPage, renderNotFoundPage } from "./seo-prerender";

export type ShareExistence = "exists" | "missing" | "unknown";

const SURVIVAL_SHARE_RE = /^\/survival\/([A-Za-z0-9_-]+)\/?$/;
const POSITIVE_TTL_MS = 10 * 60_000;
const NEGATIVE_TTL_MS = 60_000;
const CACHE_MAX = 1000;
const DEFAULT_TIMEOUT_MS = 1500;

type CacheEntry = { value: "exists" | "missing"; expires: number };
const cache = new Map<string, CacheEntry>();

export function survivalShareId(pathname: string): string | null {
  return pathname.match(SURVIVAL_SHARE_RE)?.[1] ?? null;
}

export function clearSurvivalShareCache(): void {
  cache.clear();
}

function backendBaseUrl(): string {
  return process.env.FASTAPI_URL || `http://localhost:${process.env.FASTAPI_PORT || "8001"}`;
}

export async function survivalShareExists(
  simId: string,
  opts: { fetchImpl?: typeof fetch; baseUrl?: string; timeoutMs?: number; now?: () => number } = {},
): Promise<ShareExistence> {
  const now = opts.now ?? Date.now;
  const hit = cache.get(simId);
  if (hit && hit.expires > now()) return hit.value;
  if (hit) cache.delete(simId);

  const fetchImpl = opts.fetchImpl ?? fetch;
  const url = `${opts.baseUrl ?? backendBaseUrl()}/survival-sim/results/${encodeURIComponent(simId)}`;
  let value: "exists" | "missing";
  try {
    const res = await fetchImpl(url, {
      method: "GET",
      signal: AbortSignal.timeout(opts.timeoutMs ?? DEFAULT_TIMEOUT_MS),
    });
    // Drain/abort the body; only the status matters.
    try { await res.body?.cancel(); } catch { /* ignore */ }
    if (res.status === 404) value = "missing";
    else if (res.ok) value = "exists";
    else return "unknown";
  } catch {
    return "unknown";
  }
  if (cache.size >= CACHE_MAX) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) cache.delete(oldest);
  }
  cache.set(simId, { value, expires: now() + (value === "exists" ? POSITIVE_TTL_MS : NEGATIVE_TTL_MS) });
  return value;
}

/**
 * renderHtmlPage plus the one route whose status needs the backend.
 * Every other path is unchanged and synchronous in effect.
 */
export async function renderHtmlPageWithLookups(
  shell: string,
  pathname: string,
  opts: Parameters<typeof survivalShareExists>[1] = {},
): Promise<{ status: number; html: string }> {
  const simId = survivalShareId(pathname);
  if (simId && (await survivalShareExists(simId, opts)) === "missing") {
    return renderNotFoundPage(
      shell,
      pathname,
      "This survival simulation does not exist or has been removed. Run your own free simulation at /survival-simulator.",
    );
  }
  return renderHtmlPage(shell, pathname);
}
