"use client";

import type {
  AttachmentResponse,
  ItemResponse,
  ListDetailResponse,
  ListResponse,
  UploadUrlResponse,
} from "@family-keeper/shared-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";

export function useLists(familyId: string) {
  return useQuery({
    queryKey: ["lists", familyId],
    queryFn: () =>
      apiClient<ListResponse[]>(`/v1/families/${familyId}/lists`),
    enabled: !!familyId,
  });
}

export function useListDetail(
  familyId: string,
  listId: string,
  refetchInterval: number | false = false,
) {
  return useQuery({
    queryKey: ["lists", familyId, listId],
    queryFn: () =>
      apiClient<ListDetailResponse>(
        `/v1/families/${familyId}/lists/${listId}`,
      ),
    enabled: !!familyId && !!listId,
    refetchInterval,
  });
}

export function useCreateList(familyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      name: string;
      list_type?: string;
      require_photo_completion?: boolean;
      visible_to_role?: string | null;
      editable_by_role?: string | null;
    }) =>
      apiClient<ListResponse>(`/v1/families/${familyId}/lists`, {
        method: "POST",
        body: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists", familyId] });
    },
  });
}

export function useUpdateList(familyId: string, listId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      name?: string;
      visible_to_role?: string | null;
      editable_by_role?: string | null;
      require_photo_completion?: boolean;
      is_archived?: boolean;
    }) =>
      apiClient<ListResponse>(
        `/v1/families/${familyId}/lists/${listId}`,
        { method: "PATCH", body: data },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists", familyId] });
      queryClient.invalidateQueries({
        queryKey: ["lists", familyId, listId],
      });
    },
  });
}

export function useAddItems(familyId: string, listId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (items: { content: string; assigned_to?: string }[]) =>
      apiClient<ItemResponse[]>(
        `/v1/families/${familyId}/lists/${listId}/items`,
        { method: "POST", body: { items } },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["lists", familyId, listId],
      });
    },
  });
}

export function useUpdateItem(familyId: string, listId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      itemId,
      ...data
    }: {
      itemId: string;
      content?: string;
      status?: string;
      notes?: string | null;
      assigned_to?: string | null;
      due_date?: string | null;
    }) =>
      apiClient<ItemResponse>(
        `/v1/families/${familyId}/lists/${listId}/items/${itemId}`,
        { method: "PATCH", body: data },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["lists", familyId, listId],
      });
    },
  });
}

export function useDeleteItem(familyId: string, listId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: string) =>
      apiClient<{ message: string }>(
        `/v1/families/${familyId}/lists/${listId}/items/${itemId}`,
        { method: "DELETE" },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["lists", familyId, listId],
      });
    },
  });
}

export function useReorderItems(familyId: string, listId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (items: { id: string; position: number }[]) =>
      apiClient<ItemResponse[]>(
        `/v1/families/${familyId}/lists/${listId}/items/reorder`,
        { method: "PATCH", body: { items } },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["lists", familyId, listId],
      });
    },
  });
}

export function useAttachmentUrl(
  familyId: string,
  listId: string,
  itemId: string,
  attachmentId: string,
  enabled = true,
) {
  return useQuery({
    queryKey: ["attachment-url", attachmentId],
    queryFn: () =>
      apiClient<{ url: string }>(
        `/v1/families/${familyId}/lists/${listId}/items/${itemId}/attachments/${attachmentId}/url`,
      ),
    enabled: enabled && !!attachmentId,
    staleTime: 30 * 60 * 1000, // 30 min (URL valid for 1 hour)
  });
}

export function useUploadAttachment(
  familyId: string,
  listId: string,
  itemId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      isCompletionPhoto = false,
    }: {
      file: File;
      isCompletionPhoto?: boolean;
    }) => {
      // 1. Get pre-signed upload URL
      const urlData = await apiClient<UploadUrlResponse>(
        `/v1/families/${familyId}/lists/${listId}/items/${itemId}/attachments/upload-url`,
        {
          method: "POST",
          body: {
            filename: file.name,
            mime_type: file.type,
            file_size_bytes: file.size,
            is_completion_photo: isCompletionPhoto,
          },
        },
      );

      // 2. Upload file directly to R2
      const uploadResp = await fetch(urlData.upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type },
        body: file,
      });
      if (!uploadResp.ok) {
        throw new Error("Failed to upload file to storage");
      }

      // 3. Confirm upload
      const attachment = await apiClient<AttachmentResponse>(
        `/v1/families/${familyId}/lists/${listId}/items/${itemId}/attachments/${urlData.attachment_id}/confirm`,
        { method: "POST" },
      );

      return attachment;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["lists", familyId, listId],
      });
    },
  });
}
