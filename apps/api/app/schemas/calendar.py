from pydantic import BaseModel


class CalendarEventResponse(BaseModel):
    id: str
    title: str
    start: str
    end: str | None = None
    all_day: bool
    member_name: str
    color: str


class CalendarEventsResponse(BaseModel):
    events: list[CalendarEventResponse]
    connected_members: int
    total_members: int


class GoogleOAuthStatusResponse(BaseModel):
    connected: bool
    scope: str | None = None
