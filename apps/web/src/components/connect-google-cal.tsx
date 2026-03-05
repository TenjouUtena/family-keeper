"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useDisconnectGoogle, useGoogleAuthStatus } from "@/hooks/useCalendar";
import { API_BASE_URL } from "@/lib/api-client";

export function ConnectGoogleCal() {
  const { data: status, isLoading } = useGoogleAuthStatus();
  const disconnect = useDisconnectGoogle();

  if (isLoading) return null;

  const handleConnect = async () => {
    // Get the auth token for the redirect request
    const { useAuthStore } = await import("@/stores/auth-store");
    const token = useAuthStore.getState().accessToken;
    // Open the OAuth flow — since it's a redirect, we navigate directly
    // But we need to pass the token. The backend expects Bearer auth on this endpoint.
    // Use a popup or direct navigation with token in URL isn't great.
    // Instead: open in same window — the backend will redirect to Google.
    // We pass the token as a query param that the backend will read.
    window.location.href = `${API_BASE_URL}/v1/calendar/auth/google?token=${token}`;
  };

  if (status?.connected) {
    return (
      <Card>
        <CardContent className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100">
              <svg
                className="h-4 w-4 text-green-600"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="2"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4.5 12.75l6 6 9-13.5"
                />
              </svg>
            </div>
            <span className="text-sm font-medium text-gray-700">
              Google Calendar connected
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => disconnect.mutate()}
            loading={disconnect.isPending}
          >
            Disconnect
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100">
            <svg
              className="h-4 w-4 text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="2"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5"
              />
            </svg>
          </div>
          <span className="text-sm text-gray-600">
            Connect your Google Calendar
          </span>
        </div>
        <Button size="sm" onClick={handleConnect}>
          Connect
        </Button>
      </CardContent>
    </Card>
  );
}
