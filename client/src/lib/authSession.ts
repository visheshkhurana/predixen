/**
 * Shared 401 session policy for the signup → first-insight path.
 *
 * GET 401s (onboarding company list, /overview smart-alerts, truth/decisions)
 * must not wipe the persisted user or hard-redirect to /auth. Those reads fire
 * on first paint; treating them as a dead session is the silent logout.
 *
 * Mutations still refresh, then redirect only if the session is actually gone.
 */

let _refreshingToken: Promise<boolean> | null = null;
let _redirecting401 = false;

const MUTATION_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function isMutationMethod(method?: string): boolean {
  return MUTATION_METHODS.has((method || "GET").toUpperCase());
}

export function shouldHardRedirectOn401(
  method?: string,
  pathname?: string,
): boolean {
  if (!isMutationMethod(method)) return false;
  if (pathname && pathname.startsWith("/auth")) return false;
  return true;
}

export async function attemptTokenRefresh(): Promise<boolean> {
  if (_refreshingToken) return _refreshingToken;
  _refreshingToken = (async () => {
    try {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        credentials: "include",
      });
      return res.ok;
    } catch {
      return false;
    } finally {
      _refreshingToken = null;
    }
  })();
  return _refreshingToken;
}

export function hardRedirectToLogin(): void {
  if (typeof window === "undefined") return;
  if (window.location.pathname.startsWith("/auth")) return;
  if (_redirecting401) return;
  _redirecting401 = true;

  try {
    const raw = localStorage.getItem("founderconsole-founder-storage");
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed?.state) {
        parsed.state.user = null;
        localStorage.setItem("founderconsole-founder-storage", JSON.stringify(parsed));
      }
    }
  } catch {}

  try {
    window.dispatchEvent(new CustomEvent("session-expired"));
  } catch {}

  setTimeout(() => {
    try {
      window.location.assign("/auth?expired=1");
    } catch {}
  }, 100);
}
