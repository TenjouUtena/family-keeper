"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useUploadAttachment } from "@/hooks/useLists";

const ACCEPTED_TYPES = "image/jpeg,image/png,image/webp,image/heic,image/heif";
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

type PhotoUploadProps = {
  familyId: string;
  listId: string;
  itemId: string;
  isCompletionPhoto?: boolean;
  onUploaded?: () => void;
};

export function PhotoUpload({
  familyId,
  listId,
  itemId,
  isCompletionPhoto = false,
  onUploaded,
}: PhotoUploadProps) {
  const upload = useUploadAttachment(familyId, listId, itemId);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    setError(null);

    if (!file.type.startsWith("image/")) {
      setError("Only image files are allowed");
      return;
    }
    if (file.size > MAX_SIZE) {
      setError("File must be under 10 MB");
      return;
    }

    // Show preview
    const url = URL.createObjectURL(file);
    setPreview(url);

    try {
      await upload.mutateAsync({ file, isCompletionPhoto });
      onUploaded?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setPreview(null);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset so same file can be re-selected
    e.target.value = "";
  };

  return (
    <div className="space-y-2">
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        capture="environment"
        onChange={handleChange}
        className="hidden"
      />

      <div className="flex gap-2">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
          loading={upload.isPending}
        >
          <svg
            className="mr-1.5 h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="2"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z"
            />
          </svg>
          {isCompletionPhoto ? "Take Proof Photo" : "Add Photo"}
        </Button>
      </div>

      {preview && (
        <img
          src={preview}
          alt="Upload preview"
          className="h-24 w-24 rounded-lg object-cover"
        />
      )}

      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
