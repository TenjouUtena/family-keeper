from pydantic import BaseModel


class ExtractedItem(BaseModel):
    content: str
    notes: str | None = None


class ImageToListResponse(BaseModel):
    items: list[ExtractedItem]
    input_tokens: int
    output_tokens: int


class ExtractedEvent(BaseModel):
    title: str
    start_at: str | None = None
    end_at: str | None = None
    all_day: bool = False
    location: str | None = None
    notes: str | None = None


class ImageToScheduleResponse(BaseModel):
    events: list[ExtractedEvent]
    input_tokens: int
    output_tokens: int
