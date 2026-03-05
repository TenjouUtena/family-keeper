"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

const MAX_RETRIES = 5;
const BASE_DELAY = 1000;

export function useListSSE(familyId: string, listId: string) {
  const queryClient = useQueryClient();
  const [isConnected, setIsConnected] = useState(false);
  const retriesRef = useRef(0);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!familyId || !listId) return;

    function connect() {
      const token = useAuthStore.getState().accessToken;
      if (!token) return;

      const url = `${API_BASE_URL}/v1/families/${familyId}/lists/${listId}/stream?token=${encodeURIComponent(token)}`;
      const es = new EventSource(url);
      esRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
        retriesRef.current = 0;
      };

      const handleEvent = () => {
        queryClient.invalidateQueries({
          queryKey: ["lists", familyId, listId],
        });
      };

      es.addEventListener("item_created", handleEvent);
      es.addEventListener("items_created", handleEvent);
      es.addEventListener("item_updated", handleEvent);
      es.addEventListener("item_deleted", handleEvent);
      es.addEventListener("list_updated", handleEvent);
      es.addEventListener("items_reordered", handleEvent);

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
  }, [familyId, listId, queryClient]);

  return { isConnected };
}
