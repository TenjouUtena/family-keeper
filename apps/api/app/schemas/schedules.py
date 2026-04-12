from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# --- Schedule schemas ---


class CreateScheduleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    visible_to_role: str | None = None
    editable_by_role: str | None = None


class UpdateScheduleRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    visible_to_role: str | None = None
    editable_by_role: str | None = None
    is_archived: bool | None = None


class ScheduleResponse(BaseModel):
    id: UUID
    family_id: UUID
    name: str
    description: str | None
    visible_to_role: str | None
    editable_by_role: str | None
    is_archived: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    event_count: int = 0
    upcoming_event_at: datetime | None = None

    model_config = {"from_attributes": True}


# --- Event schemas ---


class CreateEventRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    all_day: bool = False
    assigned_to: UUID | None = None
    location: str | None = Field(None, max_length=500)
    notes: str | None = None


class BulkCreateEventsRequest(BaseModel):
    events: list[CreateEventRequest] = Field(min_length=1, max_length=50)


class UpdateEventRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    status: str | None = Field(
        None, pattern=r"^(pending|in_progress|done)$"
    )
    assigned_to: UUID | None = None
    location: str | None = Field(None, max_length=500)
    notes: str | None = None


class EventResponse(BaseModel):
    id: UUID
    schedule_id: UUID
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime | None
    all_day: bool
    status: str
    assigned_to: UUID | None
    completed_at: datetime | None
    completed_by: UUID | None
    completed_by_username: str | None = None
    location: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduleDetailResponse(ScheduleResponse):
    events: list[EventResponse]
