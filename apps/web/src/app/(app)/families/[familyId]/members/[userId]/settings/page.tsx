"use client";

import { useCallback, useEffect, useState } from "react";
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

const PRESET_COLORS = [
  "#4F46E5",
  "#059669",
  "#DC2626",
  "#D97706",
  "#7C3AED",
  "#DB2777",
  "#0891B2",
  "#65A30D",
  "#EA580C",
  "#4338CA",
];

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
                  <div className="flex items-center gap-1">
                    {PRESET_COLORS.map((c) => (
                      <button
                        key={c}
                        onClick={() =>
                          changeColor(cal.google_calendar_id, c)
                        }
                        className={`h-5 w-5 rounded-full border-2 transition-transform ${
                          cal.color === c
                            ? "scale-110 border-gray-800"
                            : "border-transparent hover:scale-110"
                        }`}
                        style={{ backgroundColor: c }}
                        title={c}
                      />
                    ))}
                  </div>
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
