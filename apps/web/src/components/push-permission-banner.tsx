"use client";

import { useEffect, useState } from "react";

import { usePushNotifications } from "@/hooks/usePushNotifications";

const DISMISSED_KEY = "push-banner-dismissed";

export function PushPermissionBanner() {
  const { permission, isSubscribed, isSupported, isLoading, subscribe } =
    usePushNotifications();
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    setDismissed(localStorage.getItem(DISMISSED_KEY) === "true");
  }, []);

  const handleDismiss = () => {
    setDismissed(true);
    localStorage.setItem(DISMISSED_KEY, "true");
  };

  const handleEnable = async () => {
    await subscribe();
    handleDismiss();
  };

  // Don't show if: not supported, already subscribed, already denied, dismissed, or loading
  if (
    !isSupported ||
    isSubscribed ||
    permission === "denied" ||
    permission === "granted" ||
    dismissed ||
    isLoading
  ) {
    return null;
  }

  return (
    <div className="border-b border-indigo-200 bg-indigo-50 px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-indigo-800">
          Get notified when chores are assigned or completed.
        </p>
        <div className="flex shrink-0 gap-2">
          <button
            onClick={handleDismiss}
            className="text-sm text-indigo-600 hover:text-indigo-800"
          >
            Later
          </button>
          <button
            onClick={handleEnable}
            disabled={isLoading}
            className="rounded-lg bg-indigo-600 px-3 py-1 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Enable
          </button>
        </div>
      </div>
    </div>
  );
}
