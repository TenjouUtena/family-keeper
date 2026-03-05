"use client";

import type {
  CalendarEventsResponse,
  GoogleOAuthStatus,
} from "@family-keeper/shared-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";

export function useFamilyEvents(
  familyId: string,
  start: string,
  end: string,
) {
  return useQuery({
    queryKey: ["calendar", familyId, start, end],
    queryFn: () =>
      apiClient<CalendarEventsResponse>(
        `/v1/calendar/family/${familyId}/events?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
      ),
    enabled: !!familyId && !!start && !!end,
    staleTime: 5 * 60 * 1000, // match backend 5-min cache
  });
}

export function useGoogleAuthStatus() {
  return useQuery({
    queryKey: ["google-auth-status"],
    queryFn: () =>
      apiClient<GoogleOAuthStatus>("/v1/calendar/auth/google/status"),
  });
}

export function useDisconnectGoogle() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () =>
      apiClient<{ message: string }>("/v1/calendar/auth/google", {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["google-auth-status"] });
      queryClient.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}
