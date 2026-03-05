"use client";

import { useState } from "react";

import type { ExtractedItem } from "@family-keeper/shared-types";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ExtractedItemsPreviewProps = {
  items: ExtractedItem[];
  onConfirm: (items: ExtractedItem[]) => void;
  onCancel: () => void;
  isPending: boolean;
};

export function ExtractedItemsPreview({
  items: initialItems,
  onConfirm,
  onCancel,
  isPending,
}: ExtractedItemsPreviewProps) {
  const [items, setItems] = useState<ExtractedItem[]>(initialItems);

  const updateItem = (index: number, content: string) => {
    setItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, content } : item)),
    );
  };

  const removeItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const addItem = () => {
    setItems((prev) => [...prev, { content: "", notes: null }]);
  };

  const handleConfirm = () => {
    const nonEmpty = items.filter((item) => item.content.trim());
    if (nonEmpty.length > 0) {
      onConfirm(nonEmpty);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">
          Extracted Items ({items.length})
        </h3>
        <button
          type="button"
          onClick={addItem}
          className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
        >
          + Add item
        </button>
      </div>

      <div className="space-y-2">
        {items.map((item, index) => (
          <div key={index} className="flex items-center gap-2">
            <Input
              value={item.content}
              onChange={(e) => updateItem(index, e.target.value)}
              placeholder="Item name"
              className="flex-1"
            />
            <button
              type="button"
              onClick={() => removeItem(index)}
              className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-500"
            >
              <svg
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="2"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        ))}
      </div>

      {items.length === 0 && (
        <p className="text-center text-sm text-gray-500">
          No items extracted. Add items manually or try a different photo.
        </p>
      )}

      <div className="flex gap-2">
        <Button
          type="button"
          onClick={handleConfirm}
          loading={isPending}
          disabled={items.filter((i) => i.content.trim()).length === 0}
          className="flex-1"
        >
          Add {items.filter((i) => i.content.trim()).length} Items to List
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
