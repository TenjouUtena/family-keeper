import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: vi.fn(),
  API_BASE_URL: "http://localhost:8000",
}));

const mockSetTokens = vi.fn();
const mockSetUser = vi.fn();
const mockClearAuth = vi.fn();

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: () => ({
    setTokens: mockSetTokens,
    setUser: mockSetUser,
    clearAuth: mockClearAuth,
  }),
}));

import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/hooks/useAuth";

const mockApiClient = apiClient as ReturnType<typeof vi.fn>;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useAuth", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loginMutation calls apiClient and sets tokens", async () => {
    mockApiClient
      .mockResolvedValueOnce({
        access_token: "at",
        refresh_token: "rt",
        token_type: "bearer",
      })
      .mockResolvedValueOnce({
        id: "1",
        email: "test@test.com",
        username: "test",
      });

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(),
    });

    await result.current.loginMutation.mutateAsync({
      email: "test@test.com",
      password: "password",
    });

    await waitFor(() => {
      expect(mockSetTokens).toHaveBeenCalledWith("at", "rt");
      expect(mockSetUser).toHaveBeenCalledWith({
        id: "1",
        email: "test@test.com",
        username: "test",
      });
    });

    expect(mockApiClient).toHaveBeenCalledWith("/v1/auth/login", {
      method: "POST",
      body: { email: "test@test.com", password: "password" },
      skipAuth: true,
    });
  });

  it("registerMutation calls apiClient and sets tokens", async () => {
    mockApiClient
      .mockResolvedValueOnce({
        access_token: "at2",
        refresh_token: "rt2",
        token_type: "bearer",
      })
      .mockResolvedValueOnce({
        id: "2",
        email: "new@test.com",
        username: "newuser",
      });

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(),
    });

    await result.current.registerMutation.mutateAsync({
      email: "new@test.com",
      password: "password123",
      username: "newuser",
    });

    await waitFor(() => {
      expect(mockSetTokens).toHaveBeenCalledWith("at2", "rt2");
      expect(mockSetUser).toHaveBeenCalledWith({
        id: "2",
        email: "new@test.com",
        username: "newuser",
      });
    });

    expect(mockApiClient).toHaveBeenCalledWith("/v1/auth/register", {
      method: "POST",
      body: {
        email: "new@test.com",
        password: "password123",
        username: "newuser",
      },
      skipAuth: true,
    });
  });

  it("logoutMutation clears auth and redirects", async () => {
    mockApiClient.mockResolvedValueOnce({ message: "Logged out" });

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(),
    });

    await result.current.logoutMutation.mutateAsync();

    await waitFor(() => {
      expect(mockClearAuth).toHaveBeenCalled();
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });

  it("loginMutation error propagates", async () => {
    mockApiClient.mockRejectedValueOnce(new Error("Invalid credentials"));

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.loginMutation.mutateAsync({
        email: "bad@test.com",
        password: "wrong",
      }),
    ).rejects.toThrow("Invalid credentials");
  });

  it("googleAuthMutation calls callback endpoint", async () => {
    mockApiClient
      .mockResolvedValueOnce({
        access_token: "gat",
        refresh_token: "grt",
        token_type: "bearer",
      })
      .mockResolvedValueOnce({
        id: "3",
        email: "google@test.com",
        username: "googleuser",
      });

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(),
    });

    await result.current.googleAuthMutation.mutateAsync({
      code: "google-auth-code",
    });

    expect(mockApiClient).toHaveBeenCalledWith("/v1/auth/google/callback", {
      method: "POST",
      body: { code: "google-auth-code" },
      skipAuth: true,
    });

    await waitFor(() => {
      expect(mockSetTokens).toHaveBeenCalledWith("gat", "grt");
    });
  });

  it("logoutMutation clears auth even on API error", async () => {
    mockApiClient.mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(),
    });

    // onSettled fires regardless of success/error
    try {
      await result.current.logoutMutation.mutateAsync();
    } catch {
      // expected
    }

    await waitFor(() => {
      expect(mockClearAuth).toHaveBeenCalled();
    });
  });
});
