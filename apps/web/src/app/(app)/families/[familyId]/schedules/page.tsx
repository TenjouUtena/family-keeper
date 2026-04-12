"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import type { ScheduleResponse } from "@family-keeper/shared-types";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useSchedules } from "@/hooks/useSchedules";

function ScheduleCard({
  schedule,
  familyId,
}: {
  schedule: ScheduleResponse;
  familyId: string;
}) {
  const upcomingDate = schedule.upcoming_event_at
    ? new Date(schedule.upcoming_event_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : null;

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="flex items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600">
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
              d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
            />
          </svg>
        </div>
        <Link
          href={`/families/${familyId}/schedules/${schedule.id}`}
          className="flex min-w-0 flex-1 items-center justify-between"
        >
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {schedule.name}
            </h2>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-sm text-gray-500">
                {schedule.event_count}{" "}
                {schedule.event_count === 1 ? "event" : "events"}
              </span>
              {upcomingDate && (
                <span className="text-sm text-indigo-600">
                  Next: {upcomingDate}
                </span>
              )}
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
  );
}

export default function SchedulesPage() {
  const { familyId } = useParams<{ familyId: string }>();
  const { data: schedules, isLoading } = useSchedules(familyId);

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
          <h1 className="mt-1 text-2xl font-bold text-gray-900">Schedules</h1>
        </div>
        <Link href={`/families/${familyId}/schedules/new`}>
          <Button size="sm">New Schedule</Button>
        </Link>
      </div>

      {!schedules?.length ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-lg font-medium text-gray-900">
              No schedules yet
            </p>
            <p className="mt-1 text-gray-500">
              Create a schedule to organize events with dates and times.
            </p>
            <div className="mt-6">
              <Link href={`/families/${familyId}/schedules/new`}>
                <Button>Create First Schedule</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {schedules.map((schedule: ScheduleResponse) => (
            <ScheduleCard
              key={schedule.id}
              schedule={schedule}
              familyId={familyId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
