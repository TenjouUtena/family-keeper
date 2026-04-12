"use client";

import type {
  EventResponse,
  ScheduleDetailResponse,
  ScheduleResponse,
} from "@family-keeper/shared-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";

export function useSchedules(familyId: string) {
  return useQuery({
    queryKey: ["schedules", familyId],
    queryFn: () =>
      apiClient<ScheduleResponse[]>(`/v1/families/${familyId}/schedules`),
    enabled: !!familyId,
  });
}

export function useScheduleDetail(
  familyId: string,
  scheduleId: string,
  refetchInterval: number | false = false,
) {
  return useQuery({
    queryKey: ["schedules", familyId, scheduleId],
    queryFn: () =>
      apiClient<ScheduleDetailResponse>(
        `/v1/families/${familyId}/schedules/${scheduleId}`,
      ),
    enabled: !!familyId && !!scheduleId,
    refetchInterval,
  });
}

export function useCreateSchedule(familyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      name: string;
      description?: string | null;
      visible_to_role?: string | null;
      editable_by_role?: string | null;
    }) =>
      apiClient<ScheduleResponse>(`/v1/families/${familyId}/schedules`, {
        method: "POST",
        body: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedules", familyId] });
    },
  });
}

export function useUpdateSchedule(familyId: string, scheduleId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      name?: string;
      description?: string | null;
      visible_to_role?: string | null;
      editable_by_role?: string | null;
      is_archived?: boolean;
    }) =>
      apiClient<ScheduleResponse>(
        `/v1/families/${familyId}/schedules/${scheduleId}`,
        { method: "PATCH", body: data },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedules", familyId] });
      queryClient.invalidateQueries({
        queryKey: ["schedules", familyId, scheduleId],
      });
    },
  });
}

export function useAddEvents(familyId: string, scheduleId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (
      events: {
        title: string;
        start_at: string;
        end_at?: string | null;
        all_day?: boolean;
        assigned_to?: string | null;
        location?: string | null;
        notes?: string | null;
      }[],
    ) =>
      apiClient<EventResponse[]>(
        `/v1/families/${familyId}/schedules/${scheduleId}/events`,
        { method: "POST", body: { events } },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["schedules", familyId, scheduleId],
      });
    },
  });
}

export function useUpdateEvent(familyId: string, scheduleId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      eventId,
      ...data
    }: {
      eventId: string;
      title?: string;
      description?: string | null;
      start_at?: string;
      end_at?: string | null;
      all_day?: boolean;
      status?: string;
      assigned_to?: string | null;
      location?: string | null;
      notes?: string | null;
    }) =>
      apiClient<EventResponse>(
        `/v1/families/${familyId}/schedules/${scheduleId}/events/${eventId}`,
        { method: "PATCH", body: data },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["schedules", familyId, scheduleId],
      });
    },
  });
}

export function useDeleteEvent(familyId: string, scheduleId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (eventId: string) =>
      apiClient<{ message: string }>(
        `/v1/families/${familyId}/schedules/${scheduleId}/events/${eventId}`,
        { method: "DELETE" },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["schedules", familyId, scheduleId],
      });
    },
  });
}
