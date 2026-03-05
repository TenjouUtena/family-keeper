from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# --- List schemas ---


class CreateListRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    list_type: str = Field(
        default="todo", pattern=r"^(todo|grocery|chores|custom)$"
    )
    visible_to_role: str | None = None
    editable_by_role: str | None = None
    require_photo_completion: bool = False


class UpdateListRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    visible_to_role: str | None = None
    editable_by_role: str | None = None
    require_photo_completion: bool | None = None
    is_archived: bool | None = None


class ListResponse(BaseModel):
    id: UUID
    family_id: UUID
    name: str
    list_type: str
    visible_to_role: str | None
    editable_by_role: str | None
    require_photo_completion: bool
    is_archived: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    item_count: int = 0

    model_config = {"from_attributes": True}


class AttachmentResponse(BaseModel):
    id: UUID
    item_id: UUID
    storage_key: str
    filename: str
    mime_type: str
    file_size_bytes: int
    is_completion_photo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Item schemas ---


class CreateItemRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    notes: str | None = None
    assigned_to: UUID | None = None
    due_date: datetime | None = None
    position: int | None = None


class BulkCreateItemsRequest(BaseModel):
    items: list[CreateItemRequest] = Field(min_length=1, max_length=50)


class UpdateItemRequest(BaseModel):
    content: str | None = Field(None, min_length=1, max_length=500)
    notes: str | None = None
    status: str | None = Field(
        None, pattern=r"^(pending|in_progress|done)$"
    )
    assigned_to: UUID | None = None
    due_date: datetime | None = None
    position: int | None = None


class ReorderItemRequest(BaseModel):
    id: UUID
    position: int


class ReorderItemsRequest(BaseModel):
    items: list[ReorderItemRequest] = Field(min_length=1)


class ItemResponse(BaseModel):
    id: UUID
    list_id: UUID
    content: str
    notes: str | None
    status: str
    position: int
    assigned_to: UUID | None
    due_date: datetime | None
    completed_at: datetime | None
    completed_by: UUID | None
    completed_by_username: str | None = None
    created_at: datetime
    attachments: list[AttachmentResponse] = []

    model_config = {"from_attributes": True}


class ListDetailResponse(ListResponse):
    items: list[ItemResponse]


# --- Upload schemas ---


class UploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    file_size_bytes: int = Field(gt=0, le=10 * 1024 * 1024)
    is_completion_photo: bool = False


class UploadUrlResponse(BaseModel):
    upload_url: str
    attachment_id: str
    storage_key: str
    expires_in: int
