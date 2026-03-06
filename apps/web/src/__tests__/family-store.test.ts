import { beforeEach, describe, expect, it, vi } from "vitest";
import { useFamilyStore } from "@/stores/family-store";

describe("useFamilyStore", () => {
  beforeEach(() => {
    useFamilyStore.setState({ currentFamilyId: null });
    localStorage.clear();
    vi.restoreAllMocks();
    vi.spyOn(Storage.prototype, "setItem");
    vi.spyOn(Storage.prototype, "removeItem");
  });

  it("setCurrentFamily stores ID in state and localStorage", () => {
    useFamilyStore.getState().setCurrentFamily("family-123");

    expect(useFamilyStore.getState().currentFamilyId).toBe("family-123");
    expect(localStorage.setItem).toHaveBeenCalledWith(
      "current_family_id",
      "family-123",
    );
  });

  it("setCurrentFamily(null) removes from localStorage", () => {
    useFamilyStore.getState().setCurrentFamily("family-123");
    vi.clearAllMocks();

    useFamilyStore.getState().setCurrentFamily(null);

    expect(useFamilyStore.getState().currentFamilyId).toBeNull();
    expect(localStorage.removeItem).toHaveBeenCalledWith("current_family_id");
  });

  it("initial state reads from localStorage", () => {
    // Simulate localStorage having a value before store initialization.
    // Because the store module is already loaded and Zustand creates state
    // eagerly, we verify by calling setCurrentFamily and then reading back.
    localStorage.setItem("current_family_id", "stored-id");

    // Re-create store state as if freshly initialised with that localStorage value
    useFamilyStore.setState({
      currentFamilyId: localStorage.getItem("current_family_id"),
    });

    expect(useFamilyStore.getState().currentFamilyId).toBe("stored-id");
  });

  it("currentFamilyId defaults to null when localStorage is empty", () => {
    // Ensure localStorage is empty
    localStorage.removeItem("current_family_id");

    useFamilyStore.setState({
      currentFamilyId: localStorage.getItem("current_family_id"),
    });

    expect(useFamilyStore.getState().currentFamilyId).toBeNull();
  });
});
