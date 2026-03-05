import type { TokenResponse, UserResponse } from "@family-keeper/shared-types";
import { create } from "zustand";

import { API_BASE_URL } from "@/lib/api-client";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserResponse | null;
  isAuthenticated: boolean;
  isHydrated: boolean;

  setTokens: (access: string, refresh: string) => void;
  setUser: (user: UserResponse) => void;
  clearAuth: () => void;
  refreshTokens: () => Promise<string>;
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  isAuthenticated: false,
  isHydrated: false,

  setTokens: (access, refresh) => {
    localStorage.setItem("refresh_token", refresh);
    set({ accessToken: access, refreshToken: refresh, isAuthenticated: true });
  },

  setUser: (user) => set({ user }),

  clearAuth: () => {
    localStorage.removeItem("refresh_token");
    set({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
    });
  },

  refreshTokens: async () => {
    const { refreshToken } = get();
    if (!refreshToken) throw new Error("No refresh token");

    const res = await fetch(`${API_BASE_URL}/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      get().clearAuth();
      throw new Error("Refresh failed");
    }

    const data: TokenResponse = await res.json();
    get().setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  },

  hydrate: async () => {
    const refresh = localStorage.getItem("refresh_token");
    if (refresh) {
      set({ refreshToken: refresh });
      try {
        const accessToken = await get().refreshTokens();
        // Fetch user profile
        const userRes = await fetch(`${API_BASE_URL}/v1/users/me`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (userRes.ok) {
          const user: UserResponse = await userRes.json();
          set({ user });
        }
      } catch {
        get().clearAuth();
      }
    }
    set({ isHydrated: true });
  },
}));
