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
  arrayMove,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import type { ListResponse } from "@family-keeper/shared-types";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useLists, useReorderLists } from "@/hooks/useLists";

const typeLabels: Record<string, string> = {
  todo: "To-Do",
  grocery: "Grocery",
  chores: "Chores",
  custom: "Custom",
};

function DragHandle({
  listeners,
  attributes,
}: {
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

function SortableListCard({
  list,
  familyId,
}: {
  list: ListResponse;
  familyId: string;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: list.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 10 : undefined,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <Card className="transition-shadow hover:shadow-md">
        <CardContent className="flex items-center gap-3">
          <DragHandle listeners={listeners} attributes={attributes} />
          <Link
            href={`/families/${familyId}/lists/${list.id}`}
            className="flex min-w-0 flex-1 items-center justify-between"
          >
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {list.name}
              </h2>
              <div className="mt-1 flex items-center gap-2">
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                  {typeLabels[list.list_type] || list.list_type}
                </span>
                <span className="text-sm text-gray-500">
                  {list.item_count}{" "}
                  {list.item_count === 1 ? "item" : "items"}
                </span>
              </div>
            </div>
            <svg
              className="h-5 w-5 shrink-0 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="2"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8.25 4.5l7.5 7.5-7.5 7.5"
              />
            </svg>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}

export default function ListsPage() {
  const { familyId } = useParams<{ familyId: string }>();
  const { data: lists, isLoading } = useLists(familyId);
  const reorderLists = useReorderLists(familyId);
  const [localOrder, setLocalOrder] = useState<ListResponse[] | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 200, tolerance: 5 },
    }),
  );

  const displayLists = localOrder ?? lists;

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !displayLists) return;

    const oldIndex = displayLists.findIndex((l) => l.id === active.id);
    const newIndex = displayLists.findIndex((l) => l.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const reordered = arrayMove(displayLists, oldIndex, newIndex);
    setLocalOrder(reordered);

    const items = reordered.map((list, idx) => ({
      id: list.id,
      position: idx * 100,
    }));

    reorderLists.mutate(items, {
      onSettled: () => setLocalOrder(null),
    });
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl p-6 pb-24">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Link
            href={`/families/${familyId}`}
            className="text-sm text-indigo-600 hover:text-indigo-700"
          >
            &larr; Family
          </Link>
          <h1 className="mt-1 text-2xl font-bold text-gray-900">Lists</h1>
        </div>
        <Link href={`/families/${familyId}/lists/new`}>
          <Button size="sm">New List</Button>
        </Link>
      </div>

      {!displayLists?.length ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-lg font-medium text-gray-900">
              No lists yet
            </p>
            <p className="mt-1 text-gray-500">
              Create a grocery list, to-do list, or chore list.
            </p>
            <div className="mt-6">
              <Link href={`/families/${familyId}/lists/new`}>
                <Button>Create First List</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={displayLists.map((l) => l.id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-3">
              {displayLists.map((list: ListResponse) => (
                <SortableListCard
                  key={list.id}
                  list={list}
                  familyId={familyId}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}
    </div>
  );
}
