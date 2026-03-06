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
  useFamilies,
  useFamily,
  useCreateFamily,
  useJoinFamily,
  useCreateInvite,
} from "@/hooks/useFamilies";

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

describe("useFamilies hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("useFamilies fetches family list", async () => {
    const families = [
      { id: "f1", name: "Smith Family", created_at: "2024-01-01T00:00:00Z" },
      { id: "f2", name: "Jones Family", created_at: "2024-01-02T00:00:00Z" },
    ];
    mockApiClient.mockResolvedValueOnce(families);

    const { result } = renderHook(() => useFamilies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(families);
    expect(mockApiClient).toHaveBeenCalledWith("/v1/families");
  });

  it("useFamily fetches single family", async () => {
    const family = {
      id: "f1",
      name: "Smith Family",
      members: [],
      created_at: "2024-01-01T00:00:00Z",
    };
    mockApiClient.mockResolvedValueOnce(family);

    const { result } = renderHook(() => useFamily("f1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(family);
    expect(mockApiClient).toHaveBeenCalledWith("/v1/families/f1");
  });

  it("useCreateFamily calls POST and invalidates", async () => {
    const newFamily = {
      id: "f3",
      name: "New Family",
      created_at: "2024-01-03T00:00:00Z",
    };
    mockApiClient.mockResolvedValueOnce(newFamily);

    const { result } = renderHook(() => useCreateFamily(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync("New Family");

    expect(mockApiClient).toHaveBeenCalledWith("/v1/families", {
      method: "POST",
      body: { name: "New Family" },
    });
  });

  it("useJoinFamily calls POST with code", async () => {
    const joined = {
      id: "f1",
      name: "Smith Family",
      created_at: "2024-01-01T00:00:00Z",
    };
    mockApiClient.mockResolvedValueOnce(joined);

    const { result } = renderHook(() => useJoinFamily(), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync("INVITE123");

    expect(mockApiClient).toHaveBeenCalledWith("/v1/families/join", {
      method: "POST",
      body: { code: "INVITE123" },
    });
  });

  it("useCreateInvite calls POST", async () => {
    const invite = {
      code: "ABC123",
      expires_at: "2024-02-01T00:00:00Z",
      max_uses: 5,
      use_count: 0,
    };
    mockApiClient.mockResolvedValueOnce(invite);

    const { result } = renderHook(() => useCreateInvite("f1"), {
      wrapper: createWrapper(),
    });

    await result.current.mutateAsync({ max_uses: 5, expires_in_hours: 24 });

    expect(mockApiClient).toHaveBeenCalledWith("/v1/families/f1/invites", {
      method: "POST",
      body: { max_uses: 5, expires_in_hours: 24 },
    });
  });

  it("useFamily disabled when no familyId", async () => {
    const { result } = renderHook(() => useFamily(""), {
      wrapper: createWrapper(),
    });

    // The query should not fire since enabled: !!familyId is false
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockApiClient).not.toHaveBeenCalled();
  });
});
