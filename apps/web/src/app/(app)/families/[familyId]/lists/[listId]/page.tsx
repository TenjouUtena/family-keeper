"use client";

import {
  closestCenter,
  DndContext,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DraggableAttributes,
} from "@dnd-kit/core";
import type { SyntheticListenerMap } from "@dnd-kit/core/dist/hooks/utilities";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import type {
  FamilyMemberResponse,
  ItemResponse,
  ListDetailResponse,
} from "@family-keeper/shared-types";

import { AICaptureButton } from "@/components/ai-capture-button";
import { ItemDetail } from "@/components/item-detail";
import { ListSettings } from "@/components/list-settings";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useFamily } from "@/hooks/useFamilies";
import {
  useAddItems,
  useDeleteItem,
  useListDetail,
  useReorderItems,
  useUpdateItem,
} from "@/hooks/useLists";
import { useListSSE } from "@/hooks/useListSSE";
import { useAuthStore } from "@/stores/auth-store";

function DragHandle({ listeners, attributes }: {
  listeners?: SyntheticListenerMap;
  attributes?: DraggableAttributes;
}) {
  return (
    <button
      type="button"
      className="flex shrink-0 cursor-grab touch-none items-center text-gray-300 hover:text-gray-500 active:cursor-grabbing"
      aria-label="Drag to reorder"
      {...attributes}
      {...listeners}
    >
      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
        <path d="M7 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM7 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM7 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4z" />
      </svg>
    </button>
  );
}

function SortableItem({
  item,
  expandedId,
  setExpandedId,
  members,
  list,
  familyId,
  isParent,
  handleToggleStatus,
  deleteItem,
}: {
  item: ItemResponse;
  expandedId: string | null;
  setExpandedId: (id: string | null) => void;
  members: FamilyMemberResponse[];
  list: ListDetailResponse;
  familyId: string;
  isParent: boolean;
  handleToggleStatus: (item: ItemResponse) => void;
  deleteItem: { mutate: (id: string) => void };
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 10 : undefined,
    opacity: isDragging ? 0.5 : undefined,
  };

  const isExpanded = expandedId === item.id;
  const assignedMember = members.find((m) => m.user_id === item.assigned_to);
  const isOverdue = item.due_date && new Date(item.due_date) < new Date();

  return (
    <div ref={setNodeRef} style={style}>
      <Card>
        <CardContent className="space-y-2 py-3">
          <div className="flex items-center gap-3">
            <DragHandle listeners={listeners} attributes={attributes} />
            <button
              type="button"
              onClick={() => handleToggleStatus(item)}
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-gray-300 transition-colors hover:border-indigo-500"
              aria-label="Mark as done"
            />
            <button
              type="button"
              onClick={() => setExpandedId(isExpanded ? null : item.id)}
              className="flex min-w-0 flex-1 flex-col items-start text-left"
            >
              <span className="w-full truncate text-gray-900">
                {item.content}
              </span>
              <span className="flex gap-2 text-xs text-gray-400">
                {item.status === "in_progress" && (
                  <span className="text-indigo-500">In progress</span>
                )}
                {assignedMember && <span>{assignedMember.username}</span>}
                {item.due_date && (
                  <span className={isOverdue ? "text-red-500" : ""}>
                    {new Date(item.due_date).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })}
                    {isOverdue && " (overdue)"}
                  </span>
                )}
                {item.notes && <span>has notes</span>}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setExpandedId(isExpanded ? null : item.id)}
              className="shrink-0 text-gray-400 hover:text-gray-600"
              aria-label={isExpanded ? "Collapse details" : "Expand details"}
            >
              <svg
                className={`h-4 w-4 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="2"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                />
              </svg>
            </button>
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

          {isExpanded && (
            <ItemDetail
              item={item}
              list={list}
              familyId={familyId}
              members={members}
              isParent={isParent}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

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
  const reorderItems = useReorderItems(familyId, listId);
  const [newItem, setNewItem] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 200, tolerance: 5 },
    }),
  );

  const currentMember = family?.members.find((m) => m.user_id === user?.id);
  const isParent = currentMember?.role === "parent";
  const members = family?.members ?? [];

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

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = pendingItems.findIndex(
      (i: ItemResponse) => i.id === active.id,
    );
    const newIndex = pendingItems.findIndex(
      (i: ItemResponse) => i.id === over.id,
    );
    if (oldIndex === -1 || newIndex === -1) return;

    // Build new order and assign positions
    const reordered = [...pendingItems];
    const [moved] = reordered.splice(oldIndex, 1);
    reordered.splice(newIndex, 0, moved);

    const items = reordered.map((item: ItemResponse, idx: number) => ({
      id: item.id,
      position: idx * 100,
    }));

    reorderItems.mutate(items);
  };

  return (
    <div className="mx-auto max-w-2xl p-6 pb-24">
      <div className="mb-4">
        <Link
          href={`/families/${familyId}/lists`}
          className="text-sm text-indigo-600 hover:text-indigo-700"
        >
          &larr; Lists
        </Link>
        <div className="mt-1 flex items-center gap-2">
          <h1 className="text-2xl font-bold text-gray-900">{list.name}</h1>
          {isParent && (
            <button
              type="button"
              onClick={() => setShowSettings((v) => !v)}
              className="text-gray-400 hover:text-gray-600"
              aria-label="List settings"
            >
              <svg
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                />
              </svg>
            </button>
          )}
        </div>
        {list.require_photo_completion && (
          <span className="mt-1 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
            Photo proof required
          </span>
        )}
      </div>

      {showSettings && (
        <div className="mb-4">
          <Card>
            <ListSettings
              list={list}
              familyId={familyId}
              onClose={() => setShowSettings(false)}
            />
          </Card>
        </div>
      )}

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
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={pendingItems.map((i: ItemResponse) => i.id)}
              strategy={verticalListSortingStrategy}
            >
              {pendingItems.map((item: ItemResponse) => (
                <SortableItem
                  key={item.id}
                  item={item}
                  expandedId={expandedId}
                  setExpandedId={setExpandedId}
                  members={members}
                  list={list}
                  familyId={familyId}
                  isParent={isParent}
                  handleToggleStatus={handleToggleStatus}
                  deleteItem={deleteItem}
                />
              ))}
            </SortableContext>
          </DndContext>

          {/* Done items */}
          {doneItems.length > 0 && (
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-medium text-gray-500">
                Completed ({doneItems.length})
              </h3>
              <div className="space-y-2">
                {doneItems.map((item: ItemResponse) => {
                  const isExpanded = expandedId === item.id;

                  return (
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
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedId(isExpanded ? null : item.id)
                            }
                            className="flex min-w-0 flex-1 items-start text-left"
                          >
                            <span className="w-full truncate text-gray-500 line-through">
                              {item.content}
                            </span>
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedId(isExpanded ? null : item.id)
                            }
                            className="shrink-0 text-gray-400 hover:text-gray-600"
                            aria-label={
                              isExpanded
                                ? "Collapse details"
                                : "Expand details"
                            }
                          >
                            <svg
                              className={`h-4 w-4 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                              fill="none"
                              viewBox="0 0 24 24"
                              strokeWidth="2"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                              />
                            </svg>
                          </button>
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
                        {!isExpanded &&
                          (item.completed_by_username ||
                            item.completed_at) && (
                            <p className="ml-9 text-xs text-gray-400">
                              {item.completed_by_username && (
                                <>Done by {item.completed_by_username}</>
                              )}
                              {item.completed_at && (
                                <>
                                  {item.completed_by_username ? " " : "Done "}
                                  {new Date(
                                    item.completed_at,
                                  ).toLocaleDateString(undefined, {
                                    month: "short",
                                    day: "numeric",
                                    hour: "numeric",
                                    minute: "2-digit",
                                  })}
                                </>
                              )}
                            </p>
                          )}

                        {/* Expanded detail panel */}
                        {isExpanded && (
                          <ItemDetail
                            item={item}
                            list={list}
                            familyId={familyId}
                            members={members}
                            isParent={isParent}
                          />
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
