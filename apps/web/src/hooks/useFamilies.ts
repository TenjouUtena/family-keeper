"use client";

import type {
  FamilyDetailResponse,
  FamilyResponse,
  InviteCodeResponse,
} from "@family-keeper/shared-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";

export function useFamilies() {
  return useQuery({
    queryKey: ["families"],
    queryFn: () => apiClient<FamilyResponse[]>("/v1/families"),
  });
}

export function useFamily(familyId: string) {
  return useQuery({
    queryKey: ["families", familyId],
    queryFn: () => apiClient<FamilyDetailResponse>(`/v1/families/${familyId}`),
    enabled: !!familyId,
  });
}

export function useCreateFamily() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) =>
      apiClient<FamilyResponse>("/v1/families", {
        method: "POST",
        body: { name },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["families"] });
    },
  });
}

export function useJoinFamily() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (code: string) =>
      apiClient<FamilyResponse>("/v1/families/join", {
        method: "POST",
        body: { code },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["families"] });
    },
  });
}

export function useCreateInvite(familyId: string) {
  return useMutation({
    mutationFn: (params?: { max_uses?: number; expires_in_hours?: number }) =>
      apiClient<InviteCodeResponse>(`/v1/families/${familyId}/invites`, {
        method: "POST",
        body: params,
      }),
  });
}

export function useUpdateFamily(familyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      name?: string;
      parent_role_name?: string;
      child_role_name?: string;
    }) =>
      apiClient<FamilyResponse>(`/v1/families/${familyId}`, {
        method: "PATCH",
        body: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["families"] });
    },
  });
}

export function useRemoveMember(familyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) =>
      apiClient<{ message: string }>(
        `/v1/families/${familyId}/members/${userId}`,
        { method: "DELETE" },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["families", familyId] });
    },
  });
}

export function useUpdateMemberRole(familyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      userId,
      role,
      is_admin,
    }: {
      userId: string;
      role: string;
      is_admin?: boolean;
    }) =>
      apiClient(`/v1/families/${familyId}/members/${userId}`, {
        method: "PATCH",
        body: { role, is_admin },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["families", familyId] });
    },
  });
}
