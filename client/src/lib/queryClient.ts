import { QueryClient, QueryFunction } from "@tanstack/react-query";
import { ApiError, safeParseJSON } from "./errors";

let sessionExpiredHandled = false;

// Centralised handling for an expired/invalid session. A 401 on an authenticated
// API call means the auth cookie lapsed while the user was in the app -- before,
// this failed silently (e.g. the copilot input just cleared with no feedback).
// Now we surface it once and send the user back to sign in.
function handleSessionExpired(resUrl?: string) {
  if (sessionExpiredHandled) return;
  const url = resUrl || "";
  // Bad credentials on the auth endpoints legitimately return 401 -- that is a
  // failed login, not an expired session.
  if (/\/auth\/(login|register|admin\/login|forgot-password|refresh)/.test(url)) return;
  // Don't loop while already on the auth screen.
  if (typeof window !== "undefined" && window.location.pathname.startsWith("/auth")) return;

  sessionExpiredHandled = true;
  try {
    window.dispatchEvent(new CustomEvent("session-expired"));
  } catch {}
  // Fallback hard redirect so the user isn't stranded on a half-broken page.
  setTimeout(() => {
    try {
      window.location.assign("/auth?expired=1");
    } catch {}
  }, 200);
}

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    if (res.status === 401) {
      handleSessionExpired(res.url);
    }
    let detail: any = null;
    let message = res.statusText;

    try {
      const parsedData = await safeParseJSON(res, `Request failed (${res.status})`);
      if (parsedData) {
        detail = parsedData.detail || parsedData;
        message = detail.message || detail.detail || parsedData.message || message;
        if (typeof detail.detail === 'object') {
          detail = detail.detail;
          message = detail.message || message;
        }
      }
    } catch (parseError) {
      if (parseError instanceof ApiError) {
        throw parseError;
      }
      message = res.statusText || 'Request failed';
    }

    const error = new ApiError(res.status, `${res.status}: ${message}`, detail);
    throw error;
  }
}

function getCSRFToken(): string | null {
  const name = 'X-CSRF-Token=';
  const decodedCookie = decodeURIComponent(document.cookie);
  const cookieArray = decodedCookie.split(';');
  for (let cookie of cookieArray) {
    cookie = cookie.trim();
    if (cookie.indexOf(name) === 0) {
      return cookie.substring(name.length, cookie.length);
    }
  }
  return null;
}

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown | undefined,
): Promise<Response> {
  let res: Response;

  const makeRequest = async () => {
    const headers: Record<string, string> = {};

    if (data) {
      headers["Content-Type"] = "application/json";
    }

    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase())) {
      const csrfToken = getCSRFToken();
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }
    }

    return fetch(url, {
      method,
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: "include",
    });
  };

  try {
    res = await makeRequest();

    if (res.status === 403) {
      try {
        const body = await res.clone().json();
        if (body?.detail === 'CSRF token validation failed') {
          await fetch('/api/health', { credentials: 'include' });
          await new Promise(r => setTimeout(r, 100));
          res = await makeRequest();
        }
      } catch {}
    }
  } catch (error) {
    const networkError = error instanceof Error ? error.message : String(error);
    console.error(`Network error for ${method} ${url}:`, error);
    throw new ApiError(0, `Network request failed: ${networkError}`);
  }

  await throwIfResNotOk(res);
  return res;
}

type UnauthorizedBehavior = "returnNull" | "throw";
export const getQueryFn = <T>(options: {
  on401: UnauthorizedBehavior;
}): QueryFunction<T | null> =>
  async ({ queryKey }) => {
    const { on401: unauthorizedBehavior } = options;
    let res: Response;

    try {
      res = await fetch(queryKey.join("/") as string, {
        credentials: "include",
      });
    } catch (error) {
      const networkError = error instanceof Error ? error.message : String(error);
      console.error(`Network error for query ${queryKey.join("/")}:`, error);
      throw new ApiError(0, `Network request failed: ${networkError}`);
    }

    if (unauthorizedBehavior === "returnNull" && res.status === 401) {
      return null;
    }

    await throwIfResNotOk(res);

    try {
      return await safeParseJSON(res, 'Failed to parse query response') as T;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(res.status, 'Failed to parse query response');
    }
  };

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: getQueryFn({ on401: "throw" }),
      refetchInterval: false,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && (error.status === 401 || error.status === 403 || error.status === 404)) {
          return false;
        }
        return failureCount < 1;
      },
      throwOnError: false,
    },
    mutations: {
      retry: false,
    },
  },
});
