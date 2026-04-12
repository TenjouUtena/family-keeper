"use client";

import { useState } from "react";

import type { ExtractedEvent } from "@family-keeper/shared-types";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ExtractedEventsPreviewProps = {
  events: ExtractedEvent[];
  onConfirm: (events: ExtractedEvent[]) => void;
  onCancel: () => void;
  isPending: boolean;
};

export function ExtractedEventsPreview({
  events: initialEvents,
  onConfirm,
  onCancel,
  isPending,
}: ExtractedEventsPreviewProps) {
  const [events, setEvents] = useState<ExtractedEvent[]>(initialEvents);

  const updateEvent = (index: number, field: keyof ExtractedEvent, value: string | boolean | null) => {
    setEvents((prev) =>
      prev.map((ev, i) => (i === index ? { ...ev, [field]: value } : ev)),
    );
  };

  const removeEvent = (index: number) => {
    setEvents((prev) => prev.filter((_, i) => i !== index));
  };

  const addEvent = () => {
    setEvents((prev) => [
      ...prev,
      {
        title: "",
        start_at: null,
        end_at: null,
        all_day: false,
        location: null,
        notes: null,
      },
    ]);
  };

  const handleConfirm = () => {
    const valid = events.filter((ev) => ev.title.trim());
    if (valid.length > 0) {
      onConfirm(valid);
    }
  };

  const validCount = events.filter((ev) => ev.title.trim()).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">
          Extracted Events ({events.length})
        </h3>
        <button
          type="button"
          onClick={addEvent}
          className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
        >
          + Add event
        </button>
      </div>

      <div className="space-y-3">
        {events.map((ev, index) => (
          <div
            key={index}
            className="space-y-2 rounded-lg border border-gray-200 bg-white p-3"
          >
            <div className="flex items-center gap-2">
              <Input
                value={ev.title}
                onChange={(e) => updateEvent(index, "title", e.target.value)}
                placeholder="Event title"
                className="flex-1"
              />
              <button
                type="button"
                onClick={() => removeEvent(index)}
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
            <div className="flex gap-2">
              <input
                type="datetime-local"
                value={ev.start_at?.slice(0, 16) ?? ""}
                onChange={(e) =>
                  updateEvent(index, "start_at", e.target.value || null)
                }
                className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                placeholder="Start"
              />
              <input
                type="datetime-local"
                value={ev.end_at?.slice(0, 16) ?? ""}
                onChange={(e) =>
                  updateEvent(index, "end_at", e.target.value || null)
                }
                className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                placeholder="End"
              />
            </div>
            {(ev.location || ev.notes) && (
              <div className="flex gap-2 text-xs text-gray-500">
                {ev.location && <span>{ev.location}</span>}
                {ev.notes && <span>{ev.notes}</span>}
              </div>
            )}
          </div>
        ))}
      </div>

      {events.length === 0 && (
        <p className="text-center text-sm text-gray-500">
          No events extracted. Add events manually or try a different photo.
        </p>
      )}

      <div className="flex gap-2">
        <Button
          type="button"
          onClick={handleConfirm}
          loading={isPending}
          disabled={validCount === 0}
          className="flex-1"
        >
          Add {validCount} Events to Schedule
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
