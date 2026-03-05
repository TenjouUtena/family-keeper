export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  skipAuth?: boolean;
};

let refreshPromise: Promise<string> | null = null;

export async function apiClient<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, headers = {}, skipAuth = false } = options;

  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...headers,
  };

  // Attach access token from Zustand store
  if (!skipAuth) {
    const { useAuthStore } = await import("@/stores/auth-store");
    const accessToken = useAuthStore.getState().accessToken;
    if (accessToken) {
      requestHeaders["Authorization"] = `Bearer ${accessToken}`;
    }
  }

  let response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
  });

  // Handle 401 with token refresh (deduplicated)
  if (response.status === 401 && !skipAuth) {
    const { useAuthStore } = await import("@/stores/auth-store");
    const store = useAuthStore.getState();

    if (store.refreshToken && !refreshPromise) {
      refreshPromise = store.refreshTokens().finally(() => {
        refreshPromise = null;
      });
    }

    if (refreshPromise) {
      try {
        const newToken = await refreshPromise;
        requestHeaders["Authorization"] = `Bearer ${newToken}`;
        response = await fetch(`${API_BASE_URL}${path}`, {
          method,
          headers: requestHeaders,
          body: body ? JSON.stringify(body) : undefined,
        });
      } catch {
        store.clearAuth();
        throw new Error("Session expired");
      }
    }
  }

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail ?? `API error: ${response.status}`);
  }

  return response.json() as Promise<T>;
}
