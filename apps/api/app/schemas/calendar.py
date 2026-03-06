from pydantic import BaseModel


class CalendarEventResponse(BaseModel):
    id: str
    title: str
    start: str
    end: str | None = None
    all_day: bool
    member_name: str
    color: str
    calendar_name: str | None = None


class CalendarEventsResponse(BaseModel):
    events: list[CalendarEventResponse]
    connected_members: int
    total_members: int


class GoogleOAuthStatusResponse(BaseModel):
    connected: bool
    scope: str | None = None


# Google Calendar List (from Google API)
class GoogleCalendarListItem(BaseModel):
    id: str
    summary: str
    primary: bool = False
    color: str | None = None


class GoogleCalendarListResponse(BaseModel):
    calendars: list[GoogleCalendarListItem]


# Shared Calendar Settings
class SharedCalendarItem(BaseModel):
    google_calendar_id: str
    calendar_name: str
    color: str = "#4F46E5"
    is_enabled: bool = True


class SharedCalendarResponse(BaseModel):
    id: str
    google_calendar_id: str
    calendar_name: str
    color: str
    is_enabled: bool


class MemberCalendarSettingsUpdate(BaseModel):
    shared_calendars: list[SharedCalendarItem]


class MemberCalendarSettingsResponse(BaseModel):
    shared_calendars: list[SharedCalendarResponse]
