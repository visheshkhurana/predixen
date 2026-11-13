/**
 * How long to wait after a 429.
 *
 * Prefer the Retry-After header (delta-seconds or HTTP-date). When CORS hides
 * it, the JSON body field `retry_after` is the same number. One wait, then a
 * single retry — not the 1s/2s retry storm.
 */
const DEFAULT_BACKOFF_SECONDS = 5;
const MAX_BACKOFF_SECONDS = 60;

export function retryAfterToSeconds(value: string | null | undefined): number | null {
  if (value == null) return null;
  const text = String(value).trim();
  if (!text) return null;
  if (/^\d+(\.\d+)?$/.test(text)) {
    const seconds = Number(text);
    return Number.isFinite(seconds) ? seconds : null;
  }
  const dateMs = Date.parse(text);
  if (Number.isNaN(dateMs)) return null;
  return Math.max(0, (dateMs - Date.now()) / 1000);
}

export function backoffMsFor429(
  retryAfterHeader: string | null,
  bodyRetryAfter?: unknown,
): number {
  const fromHeader = retryAfterToSeconds(retryAfterHeader);
  const fromBody = retryAfterToSeconds(
    bodyRetryAfter == null ? null : String(bodyRetryAfter),
  );
  const seconds = fromHeader ?? fromBody ?? DEFAULT_BACKOFF_SECONDS;
  const capped = Math.min(MAX_BACKOFF_SECONDS, Math.max(0, seconds));
  return Math.round(capped * 1000);
}

export async function readBodyRetryAfter(response: Response): Promise<unknown> {
  try {
    const body = await response.clone().json();
    if (body && typeof body === "object") {
      if ("retry_after" in body) return (body as { retry_after?: unknown }).retry_after;
      if ("retryAfter" in body) return (body as { retryAfter?: unknown }).retryAfter;
    }
  } catch {
    // Non-JSON 429. The header, or the default wait, still applies.
  }
  return null;
}
