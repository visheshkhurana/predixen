// Return path through login: when a session expires we send the user to
// /auth?expired=1&next=<where they were>, and after sign-in back to it.

/**
 * Accept only same-origin app paths: "/x...", never "//host", "/\host",
 * an absolute URL, or the auth screen itself (that would loop).
 */
export function safeNextPath(raw: string | null | undefined): string | null {
  if (!raw || typeof raw !== "string") return null;
  if (raw.length > 2048) return null;
  if (!raw.startsWith("/")) return null;
  if (raw.startsWith("//") || raw.startsWith("/\\")) return null;
  if (/[\u0000-\u001f]/.test(raw)) return null;
  if (raw === "/auth" || raw.startsWith("/auth?") || raw.startsWith("/auth/")) return null;
  return raw;
}

export function buildExpiredLoginUrl(currentPath: string): string {
  const next = safeNextPath(currentPath);
  return next && next !== "/"
    ? `/auth?expired=1&next=${encodeURIComponent(next)}`
    : "/auth?expired=1";
}

/** The validated `next` from a query string, or null. */
export function readNextFromSearch(search: string): string | null {
  try {
    return safeNextPath(new URLSearchParams(search).get("next"));
  } catch {
    return null;
  }
}
