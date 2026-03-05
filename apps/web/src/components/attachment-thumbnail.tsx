"use client";

import type { AttachmentResponse } from "@family-keeper/shared-types";

import { useAttachmentUrl } from "@/hooks/useLists";

type Props = {
  familyId: string;
  listId: string;
  itemId: string;
  attachment: AttachmentResponse;
};

export function AttachmentThumbnail({
  familyId,
  listId,
  itemId,
  attachment,
}: Props) {
  const { data } = useAttachmentUrl(
    familyId,
    listId,
    itemId,
    attachment.id,
  );

  return (
    <div
      className="relative h-12 w-12 overflow-hidden rounded-md bg-gray-100"
      title={attachment.filename}
    >
      {data?.url ? (
        <a href={data.url} target="_blank" rel="noopener noreferrer">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={data.url}
            alt={attachment.filename}
            className="h-full w-full object-cover"
          />
        </a>
      ) : (
        <div className="flex h-full w-full items-center justify-center">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-transparent" />
        </div>
      )}
      {attachment.is_completion_photo && (
        <span className="absolute bottom-0 left-0 right-0 bg-green-600 text-center text-[8px] text-white">
          proof
        </span>
      )}
    </div>
  );
}
