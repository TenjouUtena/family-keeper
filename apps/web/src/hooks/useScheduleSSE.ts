"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

const MAX_RETRIES = 5;
const BASE_DELAY = 1000;

export function useScheduleSSE(familyId: string, scheduleId: string) {
  const queryClient = useQueryClient();
  const [isConnected, setIsConnected] = useState(false);
  const retriesRef = useRef(0);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!familyId || !scheduleId) return;

    function connect() {
      const token = useAuthStore.getState().accessToken;
      if (!token) return;

      const url = `${API_BASE_URL}/v1/families/${familyId}/schedules/${scheduleId}/stream?token=${encodeURIComponent(token)}`;
      const es = new EventSource(url);
      esRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
        retriesRef.current = 0;
      };

      const handleEvent = () => {
        queryClient.invalidateQueries({
          queryKey: ["schedules", familyId, scheduleId],
        });
      };

      es.addEventListener("event_created", handleEvent);
      es.addEventListener("events_created", handleEvent);
      es.addEventListener("event_updated", handleEvent);
      es.addEventListener("event_deleted", handleEvent);
      es.addEventListener("schedule_updated", handleEvent);

      es.onerror = () => {
        es.close();
        esRef.current = null;
        setIsConnected(false);

        if (retriesRef.current < MAX_RETRIES) {
          const delay = BASE_DELAY * Math.pow(2, retriesRef.current);
          retriesRef.current += 1;
          setTimeout(connect, delay);
        }
      };
    }

    connect();

    return () => {
      esRef.current?.close();
      esRef.current = null;
      setIsConnected(false);
    };
  }, [familyId, scheduleId, queryClient]);

  return { isConnected };
}
