import { QueryClient, QueryFunction } from "@tanstack/react-query";
import { ApiError, safeParseJSON } from "./errors";

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
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
      // If safeParseJSON already threw an ApiError, re-throw it
      if (parseError instanceof ApiError) {
        throw parseError;
      }
      // Otherwise continue with statusText as message
      message = res.statusText || 'Request failed';
    }

    const error = new ApiError(res.status, `${res.status}: ${message}`, detail);
    throw error;
  }
}

// Helper to get token from localStorage or Zustand persisted storage
function getAuthToken(): string | null {
  // First try direct localStorage key
  let token = localStorage.getItem('founderconsole-token');

  // Fallback: try to get from Zustand persisted storage
  if (!token) {
    try {
      const zustandStorage = localStorage.getItem('founderconsole-founder-storage');
      if (zustandStorage) {
        const parsed = JSON.parse(zustandStorage);
        token = parsed?.state?.token || null;
        // Sync back to direct key if found
        if (token) {
          localStorage.setItem('founderconsole-token', token);
        }
      }
    } catch {
      // Ignore JSON parse errors
    }
  }

  return token;
}

// Helper to get CSRF token from cookies
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

  try {
    const token = getAuthToken();
    const headers: Record<string, string> = {};

    if (data) {
      headers["Content-Type"] = "application/json";
    }
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // Include CSRF token for state-changing requests (POST, PUT, PATCH, DELETE)
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase())) {
      const csrfToken = getCSRFToken();
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }
    }

    res = await fetch(url, {
      method,
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: "include",
    });
  } catch (error) {
    const networkError = error instanceof Error ? error.message : String(error);
    console.error(`Network error for ${method} ${url}:`, error);
    throw new ApiError(0, `Network request failed: ${networkError}`);
  }

  await throwIfResNotOk(res);
  return res;
}

type UnauthorizedBehavior = "returnNull" | "throw";
export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
  async ({ queryKey }) => {
    let res: Response;

    try {
      const token = getAuthToken();
      const headers: Record<string, string> = {};

      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      res = await fetch(queryKey.join("/") as string, {
        credentials: "include",
        headers,
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
      retry: false,
    },
    mutations: {
      retry: false,
    },
  },
});
