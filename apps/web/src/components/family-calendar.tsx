"use client";

import { useCallback, useMemo, useState } from "react";
import dynamic from "next/dynamic";

import type { CalendarEvent } from "@family-keeper/shared-types";

import { useFamilyEvents } from "@/hooks/useCalendar";

// Dynamic import of FullCalendar to avoid SSR issues and reduce bundle
const FullCalendar = dynamic(
  () =>
    Promise.all([
      import("@fullcalendar/react"),
      import("@fullcalendar/daygrid"),
      import("@fullcalendar/timegrid"),
    ]).then(([{ default: FC }]) => FC),
  { ssr: false, loading: () => <CalendarSkeleton /> },
);

// We need to import plugins separately for use in the component
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";

function CalendarSkeleton() {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
    </div>
  );
}

type FamilyCalendarProps = {
  familyId: string;
};

export function FamilyCalendar({ familyId }: FamilyCalendarProps) {
  const [dateRange, setDateRange] = useState({ start: "", end: "" });
  const [calendarReady, setCalendarReady] = useState(false);

  const { data, isFetching } = useFamilyEvents(
    familyId,
    dateRange.start,
    dateRange.end,
  );

  const events = useMemo(() => {
    if (!data?.events) return [];
    return data.events.map((event: CalendarEvent) => ({
      id: event.id,
      title: `${event.title} (${event.member_name})`,
      start: event.start,
      end: event.end ?? undefined,
      allDay: event.all_day,
      backgroundColor: event.color,
      borderColor: event.color,
    }));
  }, [data?.events]);

  const handleDatesSet = useCallback(
    (arg: { startStr: string; endStr: string }) => {
      setDateRange({ start: arg.startStr, end: arg.endStr });
      setCalendarReady(true);
    },
    [],
  );

  // Member color legend
  const memberColors = useMemo(() => {
    if (!data?.events) return [];
    const seen = new Map<string, string>();
    for (const event of data.events) {
      if (!seen.has(event.member_name)) {
        seen.set(event.member_name, event.color);
      }
    }
    return Array.from(seen.entries());
  }, [data?.events]);

  return (
    <div className="space-y-4">
      {/* Member legend */}
      {memberColors.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {memberColors.map(([name, color]) => (
            <div key={name} className="flex items-center gap-1.5">
              <div
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-sm text-gray-600">{name}</span>
            </div>
          ))}
        </div>
      )}

      {/* Connection stats */}
      {data && data.total_members > 0 && (
        <p className="text-xs text-gray-500">
          {data.connected_members} of {data.total_members} members connected
        </p>
      )}

      {/* Calendar — always rendered once mounted, never unmounted */}
      <div className="relative rounded-xl border border-gray-200 bg-white p-2">
        {isFetching && calendarReady && (
          <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-white/60">
            <div className="h-6 w-6 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          </div>
        )}
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin]}
          initialView="dayGridMonth"
          headerToolbar={{
            left: "prev,next today",
            center: "title",
            right: "dayGridMonth,timeGridWeek",
          }}
          events={events}
          datesSet={handleDatesSet}
          height="auto"
          eventDisplay="block"
          dayMaxEvents={3}
        />
      </div>
    </div>
  );
}
