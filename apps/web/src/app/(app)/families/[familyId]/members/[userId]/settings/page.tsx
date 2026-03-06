"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import type {
  GoogleCalendarListItem,
  SharedCalendarSetting,
} from "@family-keeper/shared-types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  useGoogleAuthStatus,
  useGoogleCalendarList,
  useMemberCalendarSettings,
  useUpdateMemberCalendarSettings,
} from "@/hooks/useCalendar";
import { useFamily } from "@/hooks/useFamilies";
import { useAuthStore } from "@/stores/auth-store";
import { API_BASE_URL } from "@/lib/api-client";

const PRESET_COLORS: { hex: string; name: string }[] = [
  { hex: "#4F46E5", name: "Indigo" },
  { hex: "#7C3AED", name: "Violet" },
  { hex: "#DB2777", name: "Pink" },
  { hex: "#DC2626", name: "Red" },
  { hex: "#EA580C", name: "Orange" },
  { hex: "#D97706", name: "Amber" },
  { hex: "#CA8A04", name: "Yellow" },
  { hex: "#65A30D", name: "Lime" },
  { hex: "#059669", name: "Emerald" },
  { hex: "#0D9488", name: "Teal" },
  { hex: "#0891B2", name: "Cyan" },
  { hex: "#2563EB", name: "Blue" },
  { hex: "#4338CA", name: "Deep Indigo" },
  { hex: "#6D28D9", name: "Purple" },
  { hex: "#64748B", name: "Slate" },
  { hex: "#374151", name: "Charcoal" },
];

function ColorPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (color: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [hexInput, setHexInput] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const presetMatch = PRESET_COLORS.find(
    (c) => c.hex.toLowerCase() === value.toLowerCase(),
  );

  const applyHex = () => {
    const trimmed = hexInput.trim();
    if (/^#?[0-9a-fA-F]{6}$/.test(trimmed)) {
      const hex = trimmed.startsWith("#") ? trimmed : `#${trimmed}`;
      onChange(hex);
      setOpen(false);
      setHexInput("");
    }
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-md border border-gray-300 px-2 py-1.5 text-xs hover:border-gray-400 transition-colors"
      >
        <span
          className="h-4 w-4 rounded-full shrink-0"
          style={{ backgroundColor: value }}
        />
        <span className="text-gray-700 truncate max-w-20">
          {presetMatch ? presetMatch.name : value}
        </span>
        <svg
          className={`h-3 w-3 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="2"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 z-20 mt-1 w-56 rounded-lg border border-gray-200 bg-white p-3 shadow-lg">
          <div className="grid grid-cols-4 gap-1.5 mb-3">
            {PRESET_COLORS.map((c) => (
              <button
                key={c.hex}
                type="button"
                onClick={() => {
                  onChange(c.hex);
                  setOpen(false);
                }}
                className={`flex items-center justify-center h-10 rounded-md border-2 transition-all ${
                  value.toLowerCase() === c.hex.toLowerCase()
                    ? "border-gray-800 scale-105"
                    : "border-transparent hover:border-gray-300"
                }`}
                style={{ backgroundColor: c.hex }}
                title={c.name}
              >
                {value.toLowerCase() === c.hex.toLowerCase() && (
                  <svg className="h-4 w-4 text-white drop-shadow" fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                )}
              </button>
            ))}
          </div>
          <div className="border-t border-gray-100 pt-2">
            <label className="text-xs font-medium text-gray-500 mb-1 block">
              Custom hex
            </label>
            <div className="flex gap-1.5">
              <input
                type="text"
                value={hexInput}
                onChange={(e) => setHexInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applyHex()}
                placeholder="#A855F7"
                className="flex-1 rounded-md border border-gray-300 px-2 py-1 text-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                maxLength={7}
              />
              <button
                type="button"
                onClick={applyHex}
                className="rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200 transition-colors"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

type CalendarSelection = {
  google_calendar_id: string;
  calendar_name: string;
  color: string;
  is_enabled: boolean;
};

export default function MemberSettingsPage() {
  const { familyId, userId } = useParams<{
    familyId: string;
    userId: string;
  }>();
  const currentUser = useAuthStore((s) => s.user);
  const accessToken = useAuthStore((s) => s.accessToken);
  const isOwnSettings = currentUser?.id === userId;

  const { data: family, isLoading: familyLoading } = useFamily(familyId);
  const { data: authStatus } = useGoogleAuthStatus();
  const { data: googleCalendars, isLoading: calendarsLoading } =
    useGoogleCalendarList();
  const { data: existingSettings, isLoading: settingsLoading } =
    useMemberCalendarSettings(familyId, userId);
  const updateSettings = useUpdateMemberCalendarSettings(familyId);

  const [selections, setSelections] = useState<CalendarSelection[]>([]);
  const [initialized, setInitialized] = useState(false);
  const [saved, setSaved] = useState(false);

  // Initialize selections from existing settings + Google calendar list
  useEffect(() => {
    if (initialized || !googleCalendars?.calendars) return;

    const existing = existingSettings?.shared_calendars ?? [];
    const existingMap = new Map<string, SharedCalendarSetting>();
    for (const sc of existing) {
      existingMap.set(sc.google_calendar_id, sc);
    }

    const merged: CalendarSelection[] = googleCalendars.calendars.map(
      (cal: GoogleCalendarListItem) => {
        const saved = existingMap.get(cal.id);
        return {
          google_calendar_id: cal.id,
          calendar_name: cal.summary,
          color: saved?.color ?? cal.color ?? "#4F46E5",
          is_enabled: saved ? saved.is_enabled : cal.primary,
        };
      },
    );

    setSelections(merged);
    setInitialized(true);
  }, [googleCalendars, existingSettings, initialized]);

  const toggleCalendar = useCallback((calId: string) => {
    setSelections((prev) =>
      prev.map((s) =>
        s.google_calendar_id === calId ? { ...s, is_enabled: !s.is_enabled } : s,
      ),
    );
    setSaved(false);
  }, []);

  const changeColor = useCallback((calId: string, color: string) => {
    setSelections((prev) =>
      prev.map((s) =>
        s.google_calendar_id === calId ? { ...s, color } : s,
      ),
    );
    setSaved(false);
  }, []);

  const handleSave = async () => {
    await updateSettings.mutateAsync({
      shared_calendars: selections,
    });
    setSaved(true);
  };

  if (familyLoading || !family) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
      </div>
    );
  }

  const member = family.members.find((m) => m.user_id === userId);
  const memberName = member?.username ?? "Member";

  return (
    <div className="mx-auto max-w-2xl p-6">
      <Link
        href={`/families/${familyId}`}
        className="text-sm text-indigo-600 hover:text-indigo-700"
      >
        &larr; Back to {family.name}
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-gray-900">
        {isOwnSettings ? "My Settings" : `${memberName}'s Settings`}
      </h1>

      {/* Calendar Sharing Section */}
      <Card className="mt-6">
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900">
            Calendar Sharing
          </h2>
          <p className="text-sm text-gray-500">
            Choose which calendars to share with {family.name}
          </p>
        </CardHeader>
        <CardContent>
          {!isOwnSettings ? (
            <p className="text-sm text-gray-500">
              Only {memberName} can change their calendar settings.
            </p>
          ) : !authStatus?.connected ? (
            <div className="space-y-3">
              <p className="text-sm text-gray-500">
                Connect your Google Calendar to choose which calendars to share.
              </p>
              <a
                href={`${API_BASE_URL}/v1/calendar/auth/google?token=${accessToken}`}
              >
                <Button>Connect Google Calendar</Button>
              </a>
            </div>
          ) : calendarsLoading || settingsLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
            </div>
          ) : selections.length === 0 ? (
            <p className="text-sm text-gray-500">
              No calendars found in your Google account.
            </p>
          ) : (
            <div className="space-y-4">
              {selections.map((cal) => (
                <div
                  key={cal.google_calendar_id}
                  className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={cal.is_enabled}
                      onChange={() => toggleCalendar(cal.google_calendar_id)}
                      className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <div
                      className="h-4 w-4 rounded-full"
                      style={{ backgroundColor: cal.color }}
                    />
                    <span className="text-sm font-medium text-gray-900">
                      {cal.calendar_name}
                    </span>
                  </div>
                  <ColorPicker
                    value={cal.color}
                    onChange={(c) => changeColor(cal.google_calendar_id, c)}
                  />
                </div>
              ))}

              <div className="flex items-center gap-3 pt-2">
                <Button
                  onClick={handleSave}
                  loading={updateSettings.isPending}
                >
                  Save Settings
                </Button>
                {saved && (
                  <span className="text-sm text-green-600">Saved!</span>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
