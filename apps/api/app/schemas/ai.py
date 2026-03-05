from pydantic import BaseModel


class ExtractedItem(BaseModel):
    content: str
    notes: str | None = None


class ImageToListResponse(BaseModel):
    items: list[ExtractedItem]
    input_tokens: int
    output_tokens: int
