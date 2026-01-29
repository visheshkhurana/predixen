import { QueryClient, QueryFunction } from "@tanstack/react-query";

class ApiError extends Error {
  status: number;
  code?: string;
  detail?: any;
  upload_id?: string;
  
  constructor(status: number, message: string, detail?: any) {
    super(message);
    this.status = status;
    this.detail = detail;
    if (detail && typeof detail === 'object') {
      this.code = detail.code;
      this.upload_id = detail.upload_id;
    }
  }
}

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
  let token = localStorage.getItem('predixen-token');
  
  // Fallback: try to get from Zustand persisted storage
  if (!token) {
    try {
      const zustandStorage = localStorage.getItem('predixen-founder-storage');
      if (zustandStorage) {
        const parsed = JSON.parse(zustandStorage);
        token = parsed?.state?.token || null;
        // Sync back to direct key if found
        if (token) {
          localStorage.setItem('predixen-token', token);
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
      staleTime: Infinity,
      retry: false,
    },
    mutations: {
      retry: false,
    },
  },
});
