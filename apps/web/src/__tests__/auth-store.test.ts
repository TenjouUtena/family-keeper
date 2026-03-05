import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();
Object.defineProperty(globalThis, "localStorage", { value: localStorageMock });

import { useAuthStore } from "@/stores/auth-store";

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      isHydrated: false,
    });
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe("setTokens", () => {
    it("sets tokens and marks authenticated", () => {
      useAuthStore.getState().setTokens("access-123", "refresh-456");

      const state = useAuthStore.getState();
      expect(state.accessToken).toBe("access-123");
      expect(state.refreshToken).toBe("refresh-456");
      expect(state.isAuthenticated).toBe(true);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "refresh_token",
        "refresh-456",
      );
    });
  });

  describe("setUser", () => {
    it("updates user in store", () => {
      const user = {
        id: "uuid-1",
        email: "test@example.com",
        username: "testuser",
        avatar_url: null,
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
      };
      useAuthStore.getState().setUser(user);
      expect(useAuthStore.getState().user).toEqual(user);
    });
  });

  describe("clearAuth", () => {
    it("clears all auth state and localStorage", () => {
      useAuthStore.getState().setTokens("access", "refresh");
      useAuthStore.getState().clearAuth();

      const state = useAuthStore.getState();
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("refresh_token");
    });
  });

  describe("refreshTokens", () => {
    it("throws when no refresh token", async () => {
      await expect(
        useAuthStore.getState().refreshTokens(),
      ).rejects.toThrow("No refresh token");
    });

    it("calls API and updates tokens on success", async () => {
      useAuthStore.getState().setTokens("old-access", "old-refresh");

      globalThis.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            access_token: "new-access",
            refresh_token: "new-refresh",
            token_type: "bearer",
          }),
      });

      const result = await useAuthStore.getState().refreshTokens();
      expect(result).toBe("new-access");
      expect(useAuthStore.getState().accessToken).toBe("new-access");
    });

    it("clears auth on refresh failure", async () => {
      useAuthStore.getState().setTokens("old-access", "old-refresh");

      globalThis.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      await expect(
        useAuthStore.getState().refreshTokens(),
      ).rejects.toThrow("Refresh failed");
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });
  });
});
