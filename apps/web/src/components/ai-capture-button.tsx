"use client";

import { useState } from "react";

import type { ExtractedItem } from "@family-keeper/shared-types";

import { Button } from "@/components/ui/button";
import { ExtractedItemsPreview } from "@/components/extracted-items-preview";
import { ImageCapture } from "@/components/image-capture";
import { useImageToList } from "@/hooks/useAI";
import { useAddItems } from "@/hooks/useLists";

type AICaptureButtonProps = {
  familyId: string;
  listId: string;
  listType?: string;
};

type Step = "idle" | "capture" | "extracting" | "preview";

export function AICaptureButton({
  familyId,
  listId,
  listType,
}: AICaptureButtonProps) {
  const [step, setStep] = useState<Step>("idle");
  const [extractedItems, setExtractedItems] = useState<ExtractedItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const imageToList = useImageToList(familyId);
  const addItems = useAddItems(familyId, listId);

  const handleCapture = async (file: File) => {
    setStep("extracting");
    setError(null);

    try {
      const result = await imageToList.mutateAsync({
        image: file,
        listType,
      });
      setExtractedItems(result.items);
      setStep("preview");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to extract items");
      setStep("capture");
    }
  };

  const handleConfirm = async (items: ExtractedItem[]) => {
    try {
      await addItems.mutateAsync(
        items.map((item) => ({ content: item.content })),
      );
      setStep("idle");
      setExtractedItems([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add items");
    }
  };

  const handleCancel = () => {
    setStep("idle");
    setExtractedItems([]);
    setError(null);
  };

  if (step === "idle") {
    return (
      <Button
        type="button"
        variant="secondary"
        size="sm"
        onClick={() => setStep("capture")}
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
        AI Scan List
      </Button>
    );
  }

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4">
      {error && (
        <div className="mb-3 rounded-lg bg-red-50 p-2 text-sm text-red-600">
          {error}
        </div>
      )}

      {step === "capture" && (
        <ImageCapture onCapture={handleCapture} onCancel={handleCancel} />
      )}

      {step === "extracting" && (
        <div className="flex flex-col items-center gap-3 py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          <p className="text-sm text-gray-600">
            AI is reading your list...
          </p>
        </div>
      )}

      {step === "preview" && (
        <ExtractedItemsPreview
          items={extractedItems}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
          isPending={addItems.isPending}
        />
      )}
    </div>
  );
}
