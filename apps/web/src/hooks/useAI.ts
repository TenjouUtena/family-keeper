"use client";

import type { ImageToListResponse } from "@family-keeper/shared-types";
import { useMutation } from "@tanstack/react-query";

import { API_BASE_URL } from "@/lib/api-client";

export function useImageToList(familyId: string) {
  return useMutation({
    mutationFn: async ({
      image,
      listType,
    }: {
      image: File;
      listType?: string;
    }) => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const token = useAuthStore.getState().accessToken;

      const formData = new FormData();
      formData.append("image", image);
      if (listType) formData.append("list_type", listType);

      const resp = await fetch(
        `${API_BASE_URL}/v1/families/${familyId}/ai/image-to-list`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        },
      );

      if (!resp.ok) {
        const err = await resp
          .json()
          .catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail ?? `API error: ${resp.status}`);
      }

      return resp.json() as Promise<ImageToListResponse>;
    },
  });
}
