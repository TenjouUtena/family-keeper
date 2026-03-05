"use client";

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "@/lib/api-client";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, "+")
    .replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) {
    output[i] = raw.charCodeAt(i);
  }
  return output;
}

type PushState = {
  permission: NotificationPermission;
  isSubscribed: boolean;
  isLoading: boolean;
};

export function usePushNotifications() {
  const [state, setState] = useState<PushState>({
    permission: "default",
    isSubscribed: false,
    isLoading: true,
  });

  // Check current state on mount
  useEffect(() => {
    async function check() {
      if (typeof window === "undefined" || !("Notification" in window)) {
        setState({ permission: "denied", isSubscribed: false, isLoading: false });
        return;
      }

      const permission = Notification.permission;
      let isSubscribed = false;

      if (permission === "granted" && "serviceWorker" in navigator) {
        try {
          const reg = await navigator.serviceWorker.ready;
          const sub = await reg.pushManager.getSubscription();
          isSubscribed = !!sub;
        } catch {
          // SW not ready yet
        }
      }

      setState({ permission, isSubscribed, isLoading: false });
    }
    check();
  }, []);

  const subscribe = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true }));
    try {
      // Request permission
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setState({ permission, isSubscribed: false, isLoading: false });
        return;
      }

      // Get VAPID key from backend
      const { public_key } = await apiClient<{ public_key: string }>(
        "/v1/push/vapid-key",
      );

      // Subscribe via Push API
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key).buffer as ArrayBuffer,
      });

      const subJson = sub.toJSON();

      // Register with backend
      await apiClient("/v1/push/subscribe", {
        method: "POST",
        body: {
          endpoint: sub.endpoint,
          keys: {
            p256dh: subJson.keys?.p256dh ?? "",
            auth: subJson.keys?.auth ?? "",
          },
        },
      });

      setState({ permission: "granted", isSubscribed: true, isLoading: false });
    } catch (err) {
      console.error("Push subscription failed:", err);
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, []);

  const unsubscribe = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true }));
    try {
      if ("serviceWorker" in navigator) {
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.getSubscription();
        if (sub) {
          // Unregister from backend
          await apiClient("/v1/push/subscribe", {
            method: "DELETE",
            body: { endpoint: sub.endpoint },
          });
          await sub.unsubscribe();
        }
      }

      setState((s) => ({ ...s, isSubscribed: false, isLoading: false }));
    } catch (err) {
      console.error("Push unsubscribe failed:", err);
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, []);

  return {
    permission: state.permission,
    isSubscribed: state.isSubscribed,
    isLoading: state.isLoading,
    isSupported:
      typeof window !== "undefined" &&
      "Notification" in window &&
      "serviceWorker" in navigator,
    subscribe,
    unsubscribe,
  };
}
