import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api-client", () => ({
  apiClient: vi.fn(),
  API_BASE_URL: "http://localhost:8000",
}));

vi.mock("@/components/attachment-thumbnail", () => ({
  AttachmentThumbnail: ({ attachment }: { attachment: { id: string } }) => (
    <div data-testid={`attachment-${attachment.id}`}>attachment</div>
  ),
}));

vi.mock("@/components/photo-upload", () => ({
  PhotoUpload: () => <div data-testid="photo-upload">photo upload</div>,
}));

import type {
  FamilyMemberResponse,
  ItemResponse,
  ListDetailResponse,
} from "@family-keeper/shared-types";
import { apiClient } from "@/lib/api-client";
import { ItemDetail } from "@/components/item-detail";

const mockApiClient = apiClient as ReturnType<typeof vi.fn>;

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

const baseItem: ItemResponse = {
  id: "item-1",
  list_id: "list-1",
  content: "Buy groceries",
  notes: "Get organic milk",
  status: "pending",
  position: 0,
  assigned_to: "user-2",
  due_date: "2026-03-10T00:00:00Z",
  completed_at: null,
  completed_by: null,
  completed_by_username: null,
  created_at: "2026-03-01T00:00:00Z",
  attachments: [],
};

const baseList: ListDetailResponse = {
  id: "list-1",
  family_id: "fam-1",
  name: "Grocery List",
  list_type: "grocery",
  visible_to_role: null,
  editable_by_role: null,
  require_photo_completion: false,
  is_archived: false,
  created_by: "user-1",
  created_at: "2026-03-01T00:00:00Z",
  updated_at: "2026-03-01T00:00:00Z",
  item_count: 1,
  items: [baseItem],
};

const members: FamilyMemberResponse[] = [
  {
    id: "m1",
    user_id: "user-1",
    username: "Dad",
    email: "dad@test.com",
    avatar_url: null,
    role: "parent",
    is_admin: true,
    joined_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "m2",
    user_id: "user-2",
    username: "Kid",
    email: "kid@test.com",
    avatar_url: null,
    role: "child",
    is_admin: false,
    joined_at: "2026-01-01T00:00:00Z",
  },
];

const defaultProps = {
  item: baseItem,
  list: baseList,
  familyId: "fam-1",
  members,
  isParent: true,
};

describe("ItemDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all detail fields", () => {
    renderWithProviders(<ItemDetail {...defaultProps} />);

    // Notes textarea
    expect(screen.getByLabelText("Notes")).toHaveValue("Get organic milk");
    // Status dropdown
    expect(screen.getByLabelText("Status")).toHaveValue("pending");
    // Assigned to dropdown
    expect(screen.getByLabelText("Assigned to")).toHaveValue("user-2");
    // Due date input
    expect(screen.getByLabelText("Due date")).toHaveValue("2026-03-10");
  });

  it("allows editing the item name", async () => {
    mockApiClient.mockResolvedValue({
      ...baseItem,
      content: "Buy organic groceries",
    });

    renderWithProviders(<ItemDetail {...defaultProps} />);

    // Click on the name to enter edit mode
    const nameButtons = screen.getAllByRole("button", { name: "Buy groceries" });
    fireEvent.click(nameButtons[0]);

    // Input should appear
    const input = screen.getAllByDisplayValue("Buy groceries")[0];
    fireEvent.change(input, { target: { value: "Buy organic groceries" } });
    fireEvent.blur(input);

    await waitFor(() => {
      expect(mockApiClient).toHaveBeenCalledWith(
        "/v1/families/fam-1/lists/list-1/items/item-1",
        { method: "PATCH", body: { content: "Buy organic groceries" } },
      );
    });
  });

  it("allows changing status to in_progress", async () => {
    mockApiClient.mockResolvedValue({
      ...baseItem,
      status: "in_progress",
    });

    renderWithProviders(<ItemDetail {...defaultProps} />);

    fireEvent.change(screen.getByLabelText("Status"), {
      target: { value: "in_progress" },
    });

    await waitFor(() => {
      expect(mockApiClient).toHaveBeenCalledWith(
        "/v1/families/fam-1/lists/list-1/items/item-1",
        { method: "PATCH", body: { status: "in_progress" } },
      );
    });
  });

  it("allows changing assignment", async () => {
    mockApiClient.mockResolvedValue({
      ...baseItem,
      assigned_to: "user-1",
    });

    renderWithProviders(<ItemDetail {...defaultProps} />);

    fireEvent.change(screen.getByLabelText("Assigned to"), {
      target: { value: "user-1" },
    });

    await waitFor(() => {
      expect(mockApiClient).toHaveBeenCalledWith(
        "/v1/families/fam-1/lists/list-1/items/item-1",
        { method: "PATCH", body: { assigned_to: "user-1" } },
      );
    });
  });

  it("allows clearing due date", async () => {
    mockApiClient.mockResolvedValue({ ...baseItem, due_date: null });

    renderWithProviders(<ItemDetail {...defaultProps} />);

    fireEvent.click(screen.getAllByText("Clear")[0]);

    await waitFor(() => {
      expect(mockApiClient).toHaveBeenCalledWith(
        "/v1/families/fam-1/lists/list-1/items/item-1",
        { method: "PATCH", body: { due_date: null } },
      );
    });
  });

  it("shows overdue indicator for past due dates", () => {
    renderWithProviders(
      <ItemDetail
        {...defaultProps}
        item={{ ...baseItem, due_date: "2025-01-01T00:00:00Z" }}
      />,
    );

    expect(screen.getAllByText("Overdue")[0]).toBeInTheDocument();
  });

  it("shows completion info for done items", () => {
    const doneItem: ItemResponse = {
      ...baseItem,
      status: "done",
      completed_by_username: "Dad",
      completed_at: "2026-03-05T14:30:00Z",
    };

    renderWithProviders(<ItemDetail {...defaultProps} item={doneItem} />);

    expect(screen.getAllByText(/Done by Dad/)[0]).toBeInTheDocument();
  });

  it("shows photo upload when list requires completion photo", () => {
    renderWithProviders(
      <ItemDetail
        {...defaultProps}
        list={{ ...baseList, require_photo_completion: true }}
      />,
    );

    expect(screen.getAllByTestId("photo-upload")[0]).toBeInTheDocument();
  });

  it("shows attachment thumbnails", () => {
    const itemWithAttachments: ItemResponse = {
      ...baseItem,
      attachments: [
        {
          id: "att-1",
          item_id: "item-1",
          storage_key: "key",
          filename: "photo.jpg",
          mime_type: "image/jpeg",
          file_size_bytes: 1024,
          is_completion_photo: false,
          created_at: "2026-03-01T00:00:00Z",
        },
      ],
    };

    renderWithProviders(
      <ItemDetail {...defaultProps} item={itemWithAttachments} />,
    );

    expect(screen.getAllByTestId("attachment-att-1")[0]).toBeInTheDocument();
  });
});
