// Decides whether a failed query should surface a toast, and dedupes them.
//
// Without this, a failed GET leaves the page looking empty ("no data yet")
// when the truth is "the request failed". Kept free of React / DOM imports so
// server/tests/frontend-audit-ux.test.ts can unit-test it.

export interface QueryErrorMeta {
  /** Set `meta: { suppressErrorToast: true }` on a query that handles its own errors. */
  suppressErrorToast?: boolean;
}

function statusOf(error: unknown): number | undefined {
  if (error && typeof error === "object" && "status" in error) {
    const s = (error as { status: unknown }).status;
    if (typeof s === "number") return s;
  }
  return undefined;
}

/**
 * 401: the session flow (authSession.ts) already refreshes or redirects.
 * 403/404: many endpoints use these for "not on your plan" / "nothing yet",
 * which the page renders on its own. Everything else (network failure = 0,
 * 5xx, other 4xx, parse errors) is a real failure the user should see.
 */
export function shouldToastQueryError(error: unknown, meta?: Record<string, unknown> | QueryErrorMeta): boolean {
  if (meta && (meta as QueryErrorMeta).suppressErrorToast === true) return false;
  const status = statusOf(error);
  if (status === 401 || status === 403 || status === 404) return false;
  return true;
}

export function queryErrorDescription(error: unknown): string {
  const status = statusOf(error);
  if (status === 0) return "Network request failed. Check your connection and try again.";
  const message = error instanceof Error ? error.message : "";
  return message || "Something went wrong loading this data. Try again.";
}

/**
 * Wraps `notify` so the same message is shown at most once per `windowMs`
 * (one outage would otherwise toast once per failing query).
 */
export function createDedupedNotifier(
  notify: (description: string) => void,
  windowMs = 10_000,
  now: () => number = () => Date.now(),
): (error: unknown, meta?: Record<string, unknown>) => boolean {
  const lastShown = new Map<string, number>();
  return (error, meta) => {
    if (!shouldToastQueryError(error, meta)) return false;
    const description = queryErrorDescription(error);
    const t = now();
    const prev = lastShown.get(description);
    if (prev !== undefined && t - prev < windowMs) return false;
    lastShown.set(description, t);
    notify(description);
    return true;
  };
}
