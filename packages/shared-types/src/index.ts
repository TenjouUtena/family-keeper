// Shared types and Zod schemas for Family Keeper

export type HealthResponse = {
  status: "ok" | "degraded";
  db: boolean;
  redis: boolean;
};

// Auth
export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type RegisterRequest = {
  email: string;
  username: string;
  password: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

// User
export type UserResponse = {
  id: string;
  email: string;
  username: string;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string;
};

export type UserUpdateRequest = {
  username?: string;
  avatar_url?: string;
};

export type ApiError = {
  detail: string;
};

// Family
export type FamilyResponse = {
  id: string;
  name: string;
  parent_role_name: string;
  child_role_name: string;
  created_at: string;
  updated_at: string;
  member_count: number;
};

export type FamilyMemberResponse = {
  id: string;
  user_id: string;
  username: string;
  email: string;
  avatar_url: string | null;
  role: "parent" | "child";
  is_admin: boolean;
  joined_at: string;
};

export type FamilyDetailResponse = FamilyResponse & {
  members: FamilyMemberResponse[];
};

export type CreateFamilyRequest = {
  name: string;
};

export type InviteCodeResponse = {
  code: string;
  family_id: string;
  expires_at: string;
  max_uses: number;
  use_count: number;
  is_active: boolean;
  created_at: string;
};

export type JoinFamilyRequest = {
  code: string;
};

// Lists
export type ListResponse = {
  id: string;
  family_id: string;
  name: string;
  list_type: "todo" | "grocery" | "chores" | "custom";
  visible_to_role: string | null;
  editable_by_role: string | null;
  require_photo_completion: boolean;
  is_archived: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
  item_count: number;
};

export type AttachmentResponse = {
  id: string;
  item_id: string;
  storage_key: string;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  is_completion_photo: boolean;
  created_at: string;
};

export type ItemResponse = {
  id: string;
  list_id: string;
  content: string;
  notes: string | null;
  status: "pending" | "in_progress" | "done";
  position: number;
  assigned_to: string | null;
  due_date: string | null;
  completed_at: string | null;
  completed_by: string | null;
  created_at: string;
  attachments: AttachmentResponse[];
};

export type ListDetailResponse = ListResponse & {
  items: ItemResponse[];
};

export type UploadUrlRequest = {
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  is_completion_photo?: boolean;
};

export type UploadUrlResponse = {
  upload_url: string;
  attachment_id: string;
  storage_key: string;
  expires_in: number;
};
