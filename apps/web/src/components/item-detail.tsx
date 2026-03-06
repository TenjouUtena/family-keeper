"use client";

import { useEffect, useRef, useState } from "react";

import type {
  FamilyMemberResponse,
  ItemResponse,
  ListDetailResponse,
} from "@family-keeper/shared-types";

import { AttachmentThumbnail } from "@/components/attachment-thumbnail";
import { PhotoUpload } from "@/components/photo-upload";
import { useUpdateItem } from "@/hooks/useLists";

interface ItemDetailProps {
  item: ItemResponse;
  list: ListDetailResponse;
  familyId: string;
  members: FamilyMemberResponse[];
  isParent: boolean;
}

export function ItemDetail({
  item,
  list,
  familyId,
  members,
  isParent,
}: ItemDetailProps) {
  const updateItem = useUpdateItem(familyId, list.id);
  const [editingContent, setEditingContent] = useState(false);
  const [content, setContent] = useState(item.content);
  const [notes, setNotes] = useState(item.notes ?? "");
  const contentInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setContent(item.content);
    setNotes(item.notes ?? "");
  }, [item.content, item.notes]);

  useEffect(() => {
    if (editingContent) contentInputRef.current?.focus();
  }, [editingContent]);

  const handleContentSave = () => {
    setEditingContent(false);
    const trimmed = content.trim();
    if (trimmed && trimmed !== item.content) {
      updateItem.mutate({ itemId: item.id, content: trimmed });
    } else {
      setContent(item.content);
    }
  };

  const handleNotesSave = () => {
    const trimmed = notes.trim();
    const current = item.notes ?? "";
    if (trimmed !== current) {
      updateItem.mutate({
        itemId: item.id,
        notes: trimmed || null,
      });
    }
  };

  const handleAssignedToChange = (userId: string) => {
    updateItem.mutate({
      itemId: item.id,
      assigned_to: userId || null,
    });
  };

  const handleDueDateChange = (dateStr: string) => {
    updateItem.mutate({
      itemId: item.id,
      due_date: dateStr || null,
    });
  };

  const handleStatusChange = (status: string) => {
    updateItem.mutate({ itemId: item.id, status });
  };

  const assignedMember = members.find((m) => m.user_id === item.assigned_to);
  const isOverdue =
    item.due_date &&
    item.status !== "done" &&
    new Date(item.due_date) < new Date();

  const hasCompletionPhoto = item.attachments?.some(
    (a) => a.is_completion_photo,
  );
  const needsPhoto = list.require_photo_completion && !hasCompletionPhoto;

  const dueDateValue = item.due_date
    ? new Date(item.due_date).toISOString().slice(0, 10)
    : "";

  return (
    <div className="ml-9 space-y-3 border-t border-gray-100 pt-3">
      {/* Editable content */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Name
        </label>
        {editingContent ? (
          <input
            ref={contentInputRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onBlur={handleContentSave}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleContentSave();
              if (e.key === "Escape") {
                setContent(item.content);
                setEditingContent(false);
              }
            }}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            maxLength={500}
          />
        ) : (
          <button
            type="button"
            onClick={() => setEditingContent(true)}
            className="w-full rounded px-2 py-1 text-left text-sm text-gray-900 hover:bg-gray-50"
          >
            {item.content}
          </button>
        )}
      </div>

      {/* Notes */}
      <div>
        <label
          htmlFor={`notes-${item.id}`}
          className="mb-1 block text-xs font-medium text-gray-500"
        >
          Notes
        </label>
        <textarea
          id={`notes-${item.id}`}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={handleNotesSave}
          placeholder="Add notes..."
          rows={2}
          className="w-full resize-none rounded border border-gray-300 px-2 py-1 text-sm placeholder-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      {/* Status */}
      <div>
        <label
          htmlFor={`status-${item.id}`}
          className="mb-1 block text-xs font-medium text-gray-500"
        >
          Status
        </label>
        <select
          id={`status-${item.id}`}
          value={item.status}
          onChange={(e) => handleStatusChange(e.target.value)}
          disabled={item.status === "done" && !isParent}
          className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-gray-50"
        >
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="done">Done</option>
        </select>
      </div>

      {/* Assigned to */}
      <div>
        <label
          htmlFor={`assigned-${item.id}`}
          className="mb-1 block text-xs font-medium text-gray-500"
        >
          Assigned to
        </label>
        <select
          id={`assigned-${item.id}`}
          value={item.assigned_to ?? ""}
          onChange={(e) => handleAssignedToChange(e.target.value)}
          className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        >
          <option value="">Unassigned</option>
          {members.map((m) => (
            <option key={m.user_id} value={m.user_id}>
              {m.username}
            </option>
          ))}
        </select>
      </div>

      {/* Due date */}
      <div>
        <label
          htmlFor={`due-date-${item.id}`}
          className="mb-1 block text-xs font-medium text-gray-500"
        >
          Due date
        </label>
        <div className="flex items-center gap-2">
          <input
            id={`due-date-${item.id}`}
            type="date"
            value={dueDateValue}
            onChange={(e) => handleDueDateChange(e.target.value)}
            className={`flex-1 rounded border px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 ${
              isOverdue
                ? "border-red-300 text-red-600"
                : "border-gray-300 text-gray-900"
            }`}
          />
          {dueDateValue && (
            <button
              type="button"
              onClick={() => handleDueDateChange("")}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              Clear
            </button>
          )}
        </div>
        {isOverdue && (
          <p className="mt-0.5 text-xs font-medium text-red-500">Overdue</p>
        )}
      </div>

      {/* Attachments */}
      {item.attachments?.length > 0 && (
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500">
            Attachments
          </label>
          <div className="flex flex-wrap gap-2">
            {item.attachments.map((att) => (
              <AttachmentThumbnail
                key={att.id}
                familyId={familyId}
                listId={list.id}
                itemId={item.id}
                attachment={att}
              />
            ))}
          </div>
        </div>
      )}

      {/* Photo upload for completion proof */}
      {needsPhoto && item.status !== "done" && (
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500">
            Completion photo required
          </label>
          <PhotoUpload
            familyId={familyId}
            listId={list.id}
            itemId={item.id}
            isCompletionPhoto
          />
        </div>
      )}

      {/* Completed info */}
      {item.status === "done" &&
        (item.completed_by_username || item.completed_at) && (
          <p className="text-xs text-gray-400">
            {item.completed_by_username && (
              <>Done by {item.completed_by_username}</>
            )}
            {item.completed_at && (
              <>
                {item.completed_by_username ? " " : "Done "}
                {new Date(item.completed_at).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </>
            )}
          </p>
        )}
    </div>
  );
}
