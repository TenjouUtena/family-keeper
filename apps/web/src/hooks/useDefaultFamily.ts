"use client";

import { useEffect } from "react";

import { useFamilies } from "./useFamilies";

import { useFamilyStore } from "@/stores/family-store";

/**
 * Returns the default family ID for the current user.
 * Uses the stored currentFamilyId if it's still valid (user is a member),
 * otherwise falls back to the first family in the list.
 */
export function useDefaultFamily() {
  const { data: families, isLoading } = useFamilies();
  const { currentFamilyId, setCurrentFamily } = useFamilyStore();

  useEffect(() => {
    if (!families?.length) return;

    const storedIsValid =
      currentFamilyId && families.some((f) => f.id === currentFamilyId);

    if (!storedIsValid) {
      setCurrentFamily(families[0].id);
    }
  }, [families, currentFamilyId, setCurrentFamily]);

  const resolvedId =
    currentFamilyId && families?.some((f) => f.id === currentFamilyId)
      ? currentFamilyId
      : families?.[0]?.id ?? null;

  return {
    defaultFamilyId: resolvedId,
    families: families ?? [],
    isLoading,
    hasFamily: !!families?.length,
  };
}
