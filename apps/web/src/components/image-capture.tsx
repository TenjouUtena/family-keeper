"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";

const ACCEPTED_TYPES = "image/jpeg,image/png,image/webp,image/heic,image/heif";
const MAX_SIZE = 10 * 1024 * 1024;

type ImageCaptureProps = {
  onCapture: (file: File) => void;
  onCancel: () => void;
};

export function ImageCapture({ onCapture, onCancel }: ImageCaptureProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    setError(null);

    if (!file.type.startsWith("image/")) {
      setError("Only image files are allowed");
      return;
    }
    if (file.size > MAX_SIZE) {
      setError("File must be under 10 MB");
      return;
    }

    setSelectedFile(file);
    setPreview(URL.createObjectURL(file));
  };

  const handleUse = () => {
    if (selectedFile) {
      onCapture(selectedFile);
    }
  };

  const handleRetake = () => {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setSelectedFile(null);
    setError(null);
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-4">
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        capture="environment"
        onChange={handleChange}
        className="hidden"
      />

      {!preview && (
        <div className="flex flex-col items-center gap-3 rounded-xl border-2 border-dashed border-gray-300 p-8">
          <svg
            className="h-10 w-10 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.5"
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
          <p className="text-sm text-gray-500">
            Take a photo of your list or choose from gallery
          </p>
          <Button
            type="button"
            onClick={() => fileInputRef.current?.click()}
          >
            Capture Photo
          </Button>
        </div>
      )}

      {preview && (
        <div className="space-y-3">
          <img
            src={preview}
            alt="Captured list"
            className="mx-auto max-h-64 rounded-lg object-contain"
          />
          <div className="flex gap-2">
            <Button type="button" onClick={handleUse} className="flex-1">
              Use This Photo
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={handleRetake}
            >
              Retake
            </Button>
          </div>
        </div>
      )}

      {error && <p className="text-center text-sm text-red-600">{error}</p>}

      <div className="text-center">
        <button
          type="button"
          onClick={onCancel}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
