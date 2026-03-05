"use client";

import { create } from "zustand";

interface FamilyState {
  currentFamilyId: string | null;
  setCurrentFamily: (familyId: string | null) => void;
}

export const useFamilyStore = create<FamilyState>((set) => ({
  currentFamilyId:
    typeof window !== "undefined"
      ? localStorage.getItem("current_family_id")
      : null,

  setCurrentFamily: (familyId) => {
    if (familyId) {
      localStorage.setItem("current_family_id", familyId);
    } else {
      localStorage.removeItem("current_family_id");
    }
    set({ currentFamilyId: familyId });
  },
}));
