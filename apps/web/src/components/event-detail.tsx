"use client";

import { useEffect, useRef, useState } from "react";

import type {
  EventResponse,
  FamilyMemberResponse,
  ScheduleDetailResponse,
} from "@family-keeper/shared-types";

import { useUpdateEvent } from "@/hooks/useSchedules";

interface EventDetailProps {
  event: EventResponse;
  schedule: ScheduleDetailResponse;
  familyId: string;
  members: FamilyMemberResponse[];
  isParent: boolean;
}

export function EventDetail({
  event,
  schedule,
  familyId,
  members,
  isParent,
}: EventDetailProps) {
  const updateEvent = useUpdateEvent(familyId, schedule.id);
  const [editingTitle, setEditingTitle] = useState(false);
  const [title, setTitle] = useState(event.title);
  const [notes, setNotes] = useState(event.notes ?? "");
  const [location, setLocation] = useState(event.location ?? "");
  const titleInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setTitle(event.title);
    setNotes(event.notes ?? "");
    setLocation(event.location ?? "");
  }, [event.title, event.notes, event.location]);

  useEffect(() => {
    if (editingTitle) titleInputRef.current?.focus();
  }, [editingTitle]);

  const handleTitleSave = () => {
    setEditingTitle(false);
    const trimmed = title.trim();
    if (trimmed && trimmed !== event.title) {
      updateEvent.mutate({ eventId: event.id, title: trimmed });
    } else {
      setTitle(event.title);
    }
  };

  const handleNotesSave = () => {
    const trimmed = notes.trim();
    const current = event.notes ?? "";
    if (trimmed !== current) {
      updateEvent.mutate({
        eventId: event.id,
        notes: trimmed || null,
      });
    }
  };

  const handleAssignedToChange = (userId: string) => {
    updateEvent.mutate({
      eventId: event.id,
      assigned_to: userId || null,
    });
  };

  const handleStatusChange = (status: string) => {
    updateEvent.mutate({ eventId: event.id, status });
  };

  const handleStartDateChange = (dateStr: string) => {
    if (!dateStr) return;
    const existingTime = event.all_day
      ? "00:00"
      : new Date(event.start_at).toTimeString().slice(0, 5);
    updateEvent.mutate({
      eventId: event.id,
      start_at: `${dateStr}T${existingTime}:00`,
    });
  };

  const handleStartTimeChange = (timeStr: string) => {
    const existingDate = new Date(event.start_at).toISOString().slice(0, 10);
    if (timeStr) {
      updateEvent.mutate({
        eventId: event.id,
        start_at: `${existingDate}T${timeStr}:00`,
        all_day: false,
      });
    } else {
      updateEvent.mutate({
        eventId: event.id,
        all_day: true,
      });
    }
  };

  const handleEndTimeChange = (timeStr: string) => {
    if (!timeStr) {
      updateEvent.mutate({ eventId: event.id, end_at: null });
      return;
    }
    const startDate = new Date(event.start_at).toISOString().slice(0, 10);
    updateEvent.mutate({
      eventId: event.id,
      end_at: `${startDate}T${timeStr}:00`,
    });
  };

  const handleLocationSave = () => {
    const trimmed = location.trim();
    const current = event.location ?? "";
    if (trimmed !== current) {
      updateEvent.mutate({
        eventId: event.id,
        location: trimmed || null,
      });
    }
  };

  const startDateValue = new Date(event.start_at).toISOString().slice(0, 10);
  const startTimeValue = event.all_day
    ? ""
    : new Date(event.start_at).toTimeString().slice(0, 5);
  const endTimeValue =
    event.end_at && !event.all_day
      ? new Date(event.end_at).toTimeString().slice(0, 5)
      : "";

  return (
    <div className="ml-9 space-y-3 border-t border-gray-100 pt-3">
      {/* Editable title */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Title
        </label>
        {editingTitle ? (
          <input
            ref={titleInputRef}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={handleTitleSave}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleTitleSave();
              if (e.key === "Escape") {
                setTitle(event.title);
                setEditingTitle(false);
              }
            }}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            maxLength={500}
          />
        ) : (
          <button
            type="button"
            onClick={() => setEditingTitle(true)}
            className="w-full rounded px-2 py-1 text-left text-sm text-gray-900 hover:bg-gray-50"
          >
            {event.title}
          </button>
        )}
      </div>

      {/* Date and time */}
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500">
            Date
          </label>
          <input
            type="date"
            value={startDateValue}
            onChange={(e) => handleStartDateChange(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500">
            Start time
          </label>
          <input
            type="time"
            value={startTimeValue}
            onChange={(e) => handleStartTimeChange(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500">
            End time
          </label>
          <div className="flex items-center gap-1">
            <input
              type="time"
              value={endTimeValue}
              onChange={(e) => handleEndTimeChange(e.target.value)}
              className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            {endTimeValue && (
              <button
                type="button"
                onClick={() => handleEndTimeChange("")}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Location */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">
          Location
        </label>
        <input
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          onBlur={handleLocationSave}
          onKeyDown={(e) => {
            if (e.key === "Enter") (e.target as HTMLInputElement).blur();
          }}
          placeholder="Add location..."
          className="w-full rounded border border-gray-300 px-2 py-1 text-sm placeholder-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      {/* Notes */}
      <div>
        <label
          htmlFor={`notes-${event.id}`}
          className="mb-1 block text-xs font-medium text-gray-500"
        >
          Notes
        </label>
        <textarea
          id={`notes-${event.id}`}
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
          htmlFor={`status-${event.id}`}
          className="mb-1 block text-xs font-medium text-gray-500"
        >
          Status
        </label>
        <select
          id={`status-${event.id}`}
          value={event.status}
          onChange={(e) => handleStatusChange(e.target.value)}
          disabled={event.status === "done" && !isParent}
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
          htmlFor={`assigned-${event.id}`}
          className="mb-1 block text-xs font-medium text-gray-500"
        >
          Assigned to
        </label>
        <select
          id={`assigned-${event.id}`}
          value={event.assigned_to ?? ""}
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

      {/* Completed info */}
      {event.status === "done" &&
        (event.completed_by_username || event.completed_at) && (
          <p className="text-xs text-gray-400">
            {event.completed_by_username && (
              <>Done by {event.completed_by_username}</>
            )}
            {event.completed_at && (
              <>
                {event.completed_by_username ? " " : "Done "}
                {new Date(event.completed_at).toLocaleDateString(undefined, {
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
