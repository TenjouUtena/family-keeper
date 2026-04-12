"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import type {
  EventResponse,
  FamilyMemberResponse,
  ScheduleDetailResponse,
} from "@family-keeper/shared-types";

import { EventDetail } from "@/components/event-detail";
import { ExtractedEventsPreview } from "@/components/extracted-events-preview";
import { ImageCapture } from "@/components/image-capture";
import { ScheduleSettings } from "@/components/schedule-settings";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useImageToSchedule } from "@/hooks/useAI";
import { useFamily } from "@/hooks/useFamilies";
import {
  useAddEvents,
  useDeleteEvent,
  useScheduleDetail,
  useUpdateEvent,
} from "@/hooks/useSchedules";
import { useScheduleSSE } from "@/hooks/useScheduleSSE";
import { useAuthStore } from "@/stores/auth-store";

type AIScanStep = "idle" | "capture" | "extracting" | "preview";

function formatEventTime(event: EventResponse) {
  if (event.all_day) return "All day";
  const start = new Date(event.start_at);
  const time = start.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
  if (event.end_at) {
    const end = new Date(event.end_at);
    const endTime = end.toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
    });
    return `${time} - ${endTime}`;
  }
  return time;
}

function formatDateHeading(dateStr: string) {
  const date = new Date(dateStr);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === tomorrow.toDateString()) return "Tomorrow";

  return date.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

function groupEventsByDate(events: EventResponse[]) {
  const groups: Record<string, EventResponse[]> = {};
  for (const event of events) {
    const dateKey = new Date(event.start_at).toDateString();
    if (!groups[dateKey]) groups[dateKey] = [];
    groups[dateKey].push(event);
  }
  return Object.entries(groups).sort(
    ([a], [b]) => new Date(a).getTime() - new Date(b).getTime(),
  );
}

export default function ScheduleDetailPage() {
  const { familyId, scheduleId } = useParams<{
    familyId: string;
    scheduleId: string;
  }>();
  const { isConnected } = useScheduleSSE(familyId, scheduleId);
  const { data: schedule, isLoading } = useScheduleDetail(
    familyId,
    scheduleId,
    isConnected ? false : 5000,
  );
  const { data: family } = useFamily(familyId);
  const user = useAuthStore((s) => s.user);
  const addEvents = useAddEvents(familyId, scheduleId);
  const updateEvent = useUpdateEvent(familyId, scheduleId);
  const deleteEvent = useDeleteEvent(familyId, scheduleId);
  const imageToSchedule = useImageToSchedule(familyId);

  const [newTitle, setNewTitle] = useState("");
  const [newDate, setNewDate] = useState("");
  const [newTime, setNewTime] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [aiStep, setAiStep] = useState<AIScanStep>("idle");
  const [extractedEvents, setExtractedEvents] = useState<
    { title: string; start_at: string | null; end_at: string | null; all_day: boolean; location: string | null; notes: string | null }[]
  >([]);
  const [aiError, setAiError] = useState<string | null>(null);

  const currentMember = family?.members.find((m) => m.user_id === user?.id);
  const isParent = currentMember?.role === "parent";
  const members = family?.members ?? [];

  if (isLoading || !schedule) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  const handleAddEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newDate) return;
    // Build a local Date so the timezone offset is included
    const [y, m, d] = newDate.split("-").map(Number);
    let localDate: Date;
    if (newTime) {
      const [h, min] = newTime.split(":").map(Number);
      localDate = new Date(y, m - 1, d, h, min);
    } else {
      localDate = new Date(y, m - 1, d);
    }
    await addEvents.mutateAsync([
      {
        title: newTitle.trim(),
        start_at: localDate.toISOString(),
        all_day: !newTime,
      },
    ]);
    setNewTitle("");
    setNewDate("");
    setNewTime("");
  };

  const handleToggleStatus = (event: EventResponse) => {
    updateEvent.mutate({
      eventId: event.id,
      status: event.status === "done" ? "pending" : "done",
    });
  };

  const pendingEvents = schedule.events.filter(
    (e: EventResponse) => e.status !== "done",
  );
  const doneEvents = schedule.events.filter(
    (e: EventResponse) => e.status === "done",
  );
  const groupedPending = groupEventsByDate(pendingEvents);

  // AI scan handlers
  const handleAiCapture = async (file: File) => {
    setAiStep("extracting");
    setAiError(null);
    try {
      const result = await imageToSchedule.mutateAsync({ image: file });
      setExtractedEvents(result.events);
      setAiStep("preview");
    } catch (err) {
      setAiError(
        err instanceof Error ? err.message : "Failed to extract events",
      );
      setAiStep("capture");
    }
  };

  const handleAiConfirm = async (
    events: { title: string; start_at: string | null; end_at: string | null; all_day: boolean; location: string | null; notes: string | null }[],
  ) => {
    const validEvents = events
      .filter((ev) => ev.title.trim() && ev.start_at)
      .map((ev) => ({
        title: ev.title,
        start_at: ev.start_at!,
        end_at: ev.end_at,
        all_day: ev.all_day,
        location: ev.location,
        notes: ev.notes,
      }));
    if (validEvents.length > 0) {
      await addEvents.mutateAsync(validEvents);
    }
    setAiStep("idle");
    setExtractedEvents([]);
  };

  const handleAiCancel = () => {
    setAiStep("idle");
    setExtractedEvents([]);
    setAiError(null);
  };

  return (
    <div className="mx-auto max-w-2xl p-6 pb-24">
      <div className="mb-4">
        <Link
          href={`/families/${familyId}/schedules`}
          className="text-sm text-indigo-600 hover:text-indigo-700"
        >
          &larr; Schedules
        </Link>
        <div className="mt-1 flex items-center gap-2">
          <h1 className="text-2xl font-bold text-gray-900">{schedule.name}</h1>
          {isParent && (
            <button
              type="button"
              onClick={() => setShowSettings((v) => !v)}
              className="text-gray-400 hover:text-gray-600"
              aria-label="Schedule settings"
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
        {schedule.description && (
          <p className="mt-1 text-sm text-gray-500">{schedule.description}</p>
        )}
      </div>

      {showSettings && (
        <div className="mb-4">
          <Card>
            <ScheduleSettings
              schedule={schedule}
              familyId={familyId}
              onClose={() => setShowSettings(false)}
            />
          </Card>
        </div>
      )}

      {/* Add event form */}
      <form onSubmit={handleAddEvent} className="mb-4 space-y-2">
        <div className="flex gap-2">
          <Input
            placeholder="Event title..."
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            className="flex-1"
          />
          <Button
            type="submit"
            loading={addEvents.isPending}
            disabled={!newTitle.trim() || !newDate}
          >
            Add
          </Button>
        </div>
        <div className="flex gap-2">
          <input
            type="date"
            value={newDate}
            onChange={(e) => setNewDate(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            required
          />
          <input
            type="time"
            value={newTime}
            onChange={(e) => setNewTime(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="Time (optional)"
          />
        </div>
      </form>

      {/* AI Scan */}
      <div className="mb-6">
        {aiStep === "idle" && (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setAiStep("capture")}
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
            AI Scan Schedule
          </Button>
        )}

        {aiStep !== "idle" && (
          <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4">
            {aiError && (
              <div className="mb-3 rounded-lg bg-red-50 p-2 text-sm text-red-600">
                {aiError}
              </div>
            )}

            {aiStep === "capture" && (
              <ImageCapture
                onCapture={handleAiCapture}
                onCancel={handleAiCancel}
              />
            )}

            {aiStep === "extracting" && (
              <div className="flex flex-col items-center gap-3 py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
                <p className="text-sm text-gray-600">
                  AI is reading your schedule...
                </p>
              </div>
            )}

            {aiStep === "preview" && (
              <ExtractedEventsPreview
                events={extractedEvents}
                onConfirm={handleAiConfirm}
                onCancel={handleAiCancel}
                isPending={addEvents.isPending}
              />
            )}
          </div>
        )}
      </div>

      {/* Events */}
      {pendingEvents.length === 0 && doneEvents.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            No events yet. Add one above!
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {/* Pending events grouped by date */}
          {groupedPending.map(([dateKey, events]) => (
            <div key={dateKey}>
              <h3 className="mb-2 text-sm font-semibold text-gray-700">
                {formatDateHeading(dateKey)}
              </h3>
              <div className="space-y-2">
                {events.map((event: EventResponse) => {
                  const isExpanded = expandedId === event.id;
                  const assignedMember = members.find(
                    (m) => m.user_id === event.assigned_to,
                  );
                  const isPast = new Date(event.start_at) < new Date();

                  return (
                    <Card key={event.id}>
                      <CardContent className="space-y-2 py-3">
                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            onClick={() => handleToggleStatus(event)}
                            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-gray-300 transition-colors hover:border-indigo-500"
                            aria-label="Mark as done"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedId(isExpanded ? null : event.id)
                            }
                            className="flex min-w-0 flex-1 flex-col items-start text-left"
                          >
                            <span className="w-full truncate text-gray-900">
                              {event.title}
                            </span>
                            <span className="flex flex-wrap gap-2 text-xs text-gray-400">
                              <span
                                className={isPast ? "text-orange-500" : "text-indigo-500"}
                              >
                                {formatEventTime(event)}
                              </span>
                              {event.status === "in_progress" && (
                                <span className="text-indigo-500">
                                  In progress
                                </span>
                              )}
                              {assignedMember && (
                                <span>{assignedMember.username}</span>
                              )}
                              {event.location && (
                                <span>{event.location}</span>
                              )}
                            </span>
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedId(isExpanded ? null : event.id)
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
                            onClick={() => deleteEvent.mutate(event.id)}
                            className="text-gray-400 hover:text-red-500"
                            aria-label="Delete event"
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
                          <EventDetail
                            event={event}
                            schedule={schedule}
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
          ))}

          {/* Done events */}
          {doneEvents.length > 0 && (
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-medium text-gray-500">
                Completed ({doneEvents.length})
              </h3>
              <div className="space-y-2">
                {doneEvents.map((event: EventResponse) => {
                  const isExpanded = expandedId === event.id;

                  return (
                    <Card key={event.id} className="opacity-60">
                      <CardContent className="space-y-1 py-3">
                        <div className="flex items-center gap-3">
                          {isParent ? (
                            <button
                              type="button"
                              onClick={() => handleToggleStatus(event)}
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
                              setExpandedId(isExpanded ? null : event.id)
                            }
                            className="flex min-w-0 flex-1 items-start text-left"
                          >
                            <span className="w-full truncate text-gray-500 line-through">
                              {event.title}
                            </span>
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedId(isExpanded ? null : event.id)
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
                            onClick={() => deleteEvent.mutate(event.id)}
                            className="text-gray-400 hover:text-red-500"
                            aria-label="Delete event"
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
                          (event.completed_by_username ||
                            event.completed_at) && (
                            <p className="ml-9 text-xs text-gray-400">
                              {event.completed_by_username && (
                                <>Done by {event.completed_by_username}</>
                              )}
                              {event.completed_at && (
                                <>
                                  {event.completed_by_username ? " " : "Done "}
                                  {new Date(
                                    event.completed_at,
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

                        {isExpanded && (
                          <EventDetail
                            event={event}
                            schedule={schedule}
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
