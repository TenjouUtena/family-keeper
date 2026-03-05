import type {
  GoogleAuthCallbackRequest,
  GoogleAuthUrlResponse,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserResponse,
} from "@family-keeper/shared-types";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

export function useAuth() {
  const router = useRouter();
  const { setTokens, setUser, clearAuth } = useAuthStore();

  const loginMutation = useMutation({
    mutationFn: (data: LoginRequest) =>
      apiClient<TokenResponse>("/v1/auth/login", {
        method: "POST",
        body: data,
        skipAuth: true,
      }),
    onSuccess: async (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await apiClient<UserResponse>("/v1/users/me");
      setUser(user);
      router.push("/dashboard");
    },
  });

  const registerMutation = useMutation({
    mutationFn: (data: RegisterRequest) =>
      apiClient<TokenResponse>("/v1/auth/register", {
        method: "POST",
        body: data,
        skipAuth: true,
      }),
    onSuccess: async (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await apiClient<UserResponse>("/v1/users/me");
      setUser(user);
      router.push("/dashboard");
    },
  });

  const googleAuthMutation = useMutation({
    mutationFn: (data: GoogleAuthCallbackRequest) =>
      apiClient<TokenResponse>("/v1/auth/google/callback", {
        method: "POST",
        body: data,
        skipAuth: true,
      }),
    onSuccess: async (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await apiClient<UserResponse>("/v1/users/me");
      setUser(user);
      router.push("/dashboard");
    },
  });

  const getGoogleAuthUrl = async () => {
    const data = await apiClient<GoogleAuthUrlResponse>("/v1/auth/google", {
      skipAuth: true,
    });
    window.location.href = data.url;
  };

  const logoutMutation = useMutation({
    mutationFn: () =>
      apiClient<{ message: string }>("/v1/auth/logout", { method: "POST" }),
    onSettled: () => {
      clearAuth();
      router.push("/login");
    },
  });

  return { loginMutation, registerMutation, googleAuthMutation, getGoogleAuthUrl, logoutMutation };
}
