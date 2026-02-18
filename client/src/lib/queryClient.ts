import { QueryClient, QueryFunction } from "@tanstack/react-query";
import { ApiError } from "./errors";

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    let detail: any = null;
    let message = res.statusText;
    
    try {
      const text = await res.text();
      if (text) {
        try {
          detail = JSON.parse(text);
          message = detail.message || detail.detail || text;
          if (typeof detail.detail === 'object') {
            detail = detail.detail;
            message = detail.message || message;
          }
        } catch {
          message = text;
        }
      }
    } catch {
      // ignore read errors
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

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown | undefined,
): Promise<Response> {
  const token = getAuthToken();
  const headers: Record<string, string> = {};
  
  if (data) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  const res = await fetch(url, {
    method,
    headers,
    body: data ? JSON.stringify(data) : undefined,
    credentials: "include",
  });

  await throwIfResNotOk(res);
  return res;
}

type UnauthorizedBehavior = "returnNull" | "throw";
export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
  async ({ queryKey }) => {
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    const res = await fetch(queryKey.join("/") as string, {
      credentials: "include",
      headers,
    });

    if (unauthorizedBehavior === "returnNull" && res.status === 401) {
      return null;
    }

    await throwIfResNotOk(res);
    return await res.json();
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
