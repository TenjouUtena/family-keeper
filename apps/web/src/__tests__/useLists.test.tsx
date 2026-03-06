import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

vi.mock("@/lib/api-client", () => ({
  apiClient: vi.fn(),
  API_BASE_URL: "http://localhost:8000",
}));

import { apiClient } from "@/lib/api-client";
import {
  useLists,
  useCreateList,
  useAddItems,
  useUpdateItem,
  useDeleteItem,
} from "@/hooks/useLists";

const mockApiClient = apiClient as ReturnType<typeof vi.fn>;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useLists hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("useLists fetches lists for family", async () => {
    const lists = [
      { id: "l1", name: "Groceries", list_type: "grocery", family_id: "f1" },
      { id: "l2", name: "Chores", list_type: "todo", family_id: "f1" },
    ];
    mockApiClient.mockResolvedValueOnce(lists);

    const { result } = renderHook(() => useLists("f1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(lists);
    expect(mockApiClient).toHaveBeenCalledWith("/v1/families/f1/lists");
  });

  it("useCreateList calls POST", async () => {
    const newList = {
      id: "l3",
      name: "Shopping",
      list_type: "grocery",
      family_id: "f1",
    };
    mockApiClient.mockResolvedValueOnce(newList);

    const { result } = renderHook(() => useCreateList("f1"), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({
      name: "Shopping",
      list_type: "grocery",
    });

    expect(mockApiClient).toHaveBeenCalledWith("/v1/families/f1/lists", {
      method: "POST",
      body: { name: "Shopping", list_type: "grocery" },
    });
  });

  it("useAddItems calls POST with items array", async () => {
    const items = [
      { id: "i1", content: "Milk", status: "pending" },
      { id: "i2", content: "Bread", status: "pending" },
    ];
    mockApiClient.mockResolvedValueOnce(items);

    const { result } = renderHook(() => useAddItems("f1", "l1"), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync([
      { content: "Milk" },
      { content: "Bread" },
    ]);

    expect(mockApiClient).toHaveBeenCalledWith(
      "/v1/families/f1/lists/l1/items",
      {
        method: "POST",
        body: { items: [{ content: "Milk" }, { content: "Bread" }] },
      },
    );
  });

  it("useUpdateItem calls PATCH with itemId in URL", async () => {
    const updated = { id: "i1", content: "Milk", status: "done" };
    mockApiClient.mockResolvedValueOnce(updated);

    const { result } = renderHook(() => useUpdateItem("f1", "l1"), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({ itemId: "i1", status: "done" });

    expect(mockApiClient).toHaveBeenCalledWith(
      "/v1/families/f1/lists/l1/items/i1",
      {
        method: "PATCH",
        body: { status: "done" },
      },
    );
  });

  it("useDeleteItem calls DELETE", async () => {
    mockApiClient.mockResolvedValueOnce({ message: "Deleted" });

    const { result } = renderHook(() => useDeleteItem("f1", "l1"), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync("i1");

    expect(mockApiClient).toHaveBeenCalledWith(
      "/v1/families/f1/lists/l1/items/i1",
      { method: "DELETE" },
    );
  });
});
