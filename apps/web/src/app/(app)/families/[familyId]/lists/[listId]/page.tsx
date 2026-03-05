"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import type { ItemResponse } from "@family-keeper/shared-types";

import { AICaptureButton } from "@/components/ai-capture-button";
import { AttachmentThumbnail } from "@/components/attachment-thumbnail";
import { PhotoUpload } from "@/components/photo-upload";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useFamily } from "@/hooks/useFamilies";
import {
  useAddItems,
  useDeleteItem,
  useListDetail,
  useUpdateItem,
} from "@/hooks/useLists";
import { useListSSE } from "@/hooks/useListSSE";
import { useAuthStore } from "@/stores/auth-store";

export default function ListDetailPage() {
  const { familyId, listId } = useParams<{
    familyId: string;
    listId: string;
  }>();
  const { isConnected } = useListSSE(familyId, listId);
  const { data: list, isLoading } = useListDetail(
    familyId,
    listId,
    isConnected ? false : 5000,
  );
  const { data: family } = useFamily(familyId);
  const user = useAuthStore((s) => s.user);
  const addItems = useAddItems(familyId, listId);
  const updateItem = useUpdateItem(familyId, listId);
  const deleteItem = useDeleteItem(familyId, listId);
  const [newItem, setNewItem] = useState("");

  const currentMember = family?.members.find((m) => m.user_id === user?.id);
  const isParent = currentMember?.role === "parent";

  if (isLoading || !list) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItem.trim()) return;
    await addItems.mutateAsync([{ content: newItem.trim() }]);
    setNewItem("");
  };

  const handleToggleStatus = (item: ItemResponse) => {
    updateItem.mutate({
      itemId: item.id,
      status: item.status === "done" ? "pending" : "done",
    });
  };

  const pendingItems = list.items.filter(
    (i: ItemResponse) => i.status !== "done",
  );
  const doneItems = list.items.filter(
    (i: ItemResponse) => i.status === "done",
  );

  return (
    <div className="mx-auto max-w-2xl p-6 pb-24">
      <div className="mb-4">
        <Link
          href={`/families/${familyId}/lists`}
          className="text-sm text-indigo-600 hover:text-indigo-700"
        >
          &larr; Lists
        </Link>
        <h1 className="mt-1 text-2xl font-bold text-gray-900">{list.name}</h1>
        {list.require_photo_completion && (
          <span className="mt-1 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
            Photo proof required
          </span>
        )}
      </div>

      {/* Add item form */}
      <form onSubmit={handleAddItem} className="mb-4 flex gap-2">
        <Input
          placeholder="Add an item..."
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          className="flex-1"
        />
        <Button
          type="submit"
          loading={addItems.isPending}
          disabled={!newItem.trim()}
        >
          Add
        </Button>
      </form>

      {/* AI Scan */}
      <div className="mb-6">
        <AICaptureButton
          familyId={familyId}
          listId={listId}
          listType={list.list_type}
        />
      </div>

      {/* Pending items */}
      {pendingItems.length === 0 && doneItems.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            No items yet. Add one above!
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {pendingItems.map((item: ItemResponse) => {
            const hasCompletionPhoto = item.attachments?.some(
              (a) => a.is_completion_photo,
            );
            const needsPhoto =
              list.require_photo_completion && !hasCompletionPhoto;

            return (
              <Card key={item.id}>
                <CardContent className="space-y-2 py-3">
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => handleToggleStatus(item)}
                      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-gray-300 transition-colors hover:border-indigo-500"
                      aria-label="Mark as done"
                    />
                    <span className="flex-1 text-gray-900">
                      {item.content}
                    </span>
                    {item.notes && (
                      <span className="text-xs text-gray-400">
                        {item.notes}
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => deleteItem.mutate(item.id)}
                      className="text-gray-400 hover:text-red-500"
                      aria-label="Delete item"
                    >
                      <svg
                        className="h-4 w-4"
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

                  {/* Attachment thumbnails */}
                  {item.attachments?.length > 0 && (
                    <div className="ml-9 flex gap-2">
                      {item.attachments.map((att) => (
                        <AttachmentThumbnail
                          key={att.id}
                          familyId={familyId}
                          listId={listId}
                          itemId={item.id}
                          attachment={att}
                        />
                      ))}
                    </div>
                  )}

                  {/* Photo upload for items needing proof */}
                  {needsPhoto && (
                    <div className="ml-9">
                      <PhotoUpload
                        familyId={familyId}
                        listId={listId}
                        itemId={item.id}
                        isCompletionPhoto
                      />
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}

          {/* Done items */}
          {doneItems.length > 0 && (
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-medium text-gray-500">
                Completed ({doneItems.length})
              </h3>
              <div className="space-y-2">
                {doneItems.map((item: ItemResponse) => (
                  <Card key={item.id} className="opacity-60">
                    <CardContent className="space-y-1 py-3">
                      <div className="flex items-center gap-3">
                        {isParent ? (
                          <button
                            type="button"
                            onClick={() => handleToggleStatus(item)}
                            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-indigo-500 bg-indigo-500 text-white"
                            aria-label="Mark as pending"
                          >
                            <svg
                              className="h-3.5 w-3.5"
                              fill="none"
                              viewBox="0 0 24 24"
                              strokeWidth="3"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M4.5 12.75l6 6 9-13.5"
                              />
                            </svg>
                          </button>
                        ) : (
                          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-indigo-500 bg-indigo-500 text-white">
                            <svg
                              className="h-3.5 w-3.5"
                              fill="none"
                              viewBox="0 0 24 24"
                              strokeWidth="3"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M4.5 12.75l6 6 9-13.5"
                              />
                            </svg>
                          </div>
                        )}
                        <span className="flex-1 text-gray-500 line-through">
                          {item.content}
                        </span>
                        <button
                          type="button"
                          onClick={() => deleteItem.mutate(item.id)}
                          className="text-gray-400 hover:text-red-500"
                          aria-label="Delete item"
                        >
                          <svg
                            className="h-4 w-4"
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
                      {(item.completed_by_username || item.completed_at) && (
                        <p className="ml-9 text-xs text-gray-400">
                          {item.completed_by_username && (
                            <>Done by {item.completed_by_username}</>
                          )}
                          {item.completed_at && (
                            <>
                              {item.completed_by_username ? " " : "Done "}
                              {new Date(item.completed_at).toLocaleDateString(
                                undefined,
                                {
                                  month: "short",
                                  day: "numeric",
                                  hour: "numeric",
                                  minute: "2-digit",
                                },
                              )}
                            </>
                          )}
                        </p>
                      )}
                      {item.attachments?.length > 0 && (
                        <div className="ml-9 flex gap-2">
                          {item.attachments.map((att) => (
                            <AttachmentThumbnail
                              key={att.id}
                              familyId={familyId}
                              listId={listId}
                              itemId={item.id}
                              attachment={att}
                            />
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
