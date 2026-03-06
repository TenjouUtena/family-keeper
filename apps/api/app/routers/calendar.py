from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.permissions import RequireFamilyMember
from app.core.security import decode_token
from app.database import get_db
from app.models import FamilyMember, User
from app.models.google_oauth import GoogleOAuthCredential
from app.schemas import MessageResponse
from app.schemas.calendar import (
    CalendarEventsResponse,
    GoogleCalendarListResponse,
    GoogleOAuthStatusResponse,
    MemberCalendarSettingsResponse,
    MemberCalendarSettingsUpdate,
    SharedCalendarResponse,
)
from app.services.calendar_service import CalendarService

router = APIRouter(tags=["calendar"])


@router.get("/v1/calendar/auth/google")
async def google_auth_redirect(
    token: str = Query(..., description="Bearer access token (passed as query param for redirect)"),
    db: AsyncSession = Depends(get_db),
):
    """Redirect user to Google OAuth consent screen.

    Since this is a browser redirect, the access token is passed as a query
    parameter instead of the Authorization header.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id = UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    service = CalendarService(db)
    auth_url = service.build_auth_url(user_id)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/v1/calendar/auth/google/callback")
async def google_auth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback — exchange code, store tokens, redirect to frontend."""
    try:
        payload = decode_token(state)
        if payload.get("type") != "google_oauth":
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        user_id = UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    service = CalendarService(db)
    await service.exchange_code(code, user_id)

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/families?google_connected=true",
        status_code=302,
    )


@router.get(
    "/v1/calendar/auth/google/status",
    response_model=GoogleOAuthStatusResponse,
)
async def google_auth_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if current user has connected Google Calendar."""
    result = await db.execute(
        select(GoogleOAuthCredential).where(GoogleOAuthCredential.user_id == current_user.id)
    )
    cred = result.scalar_one_or_none()
    return GoogleOAuthStatusResponse(
        connected=cred is not None,
        scope=cred.scope if cred else None,
    )


@router.delete(
    "/v1/calendar/auth/google",
    response_model=MessageResponse,
)
async def disconnect_google(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect Google Calendar for current user."""
    result = await db.execute(
        select(GoogleOAuthCredential).where(GoogleOAuthCredential.user_id == current_user.id)
    )
    cred = result.scalar_one_or_none()
    if cred:
        await db.delete(cred)
        await db.commit()
    return MessageResponse(message="Google Calendar disconnected")


@router.get(
    "/v1/calendar/family/{family_id}/events",
    response_model=CalendarEventsResponse,
)
async def get_family_events(
    family_id: UUID,
    start: datetime = Query(...),
    end: datetime = Query(...),
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
):
    """Get merged calendar events for all connected family members."""
    service = CalendarService(db)
    return await service.get_family_events(family_id, start, end)


@router.get(
    "/v1/calendar/google/calendars",
    response_model=GoogleCalendarListResponse,
)
async def list_google_calendars(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all Google calendars for the current user."""
    service = CalendarService(db)
    calendars = await service.list_google_calendars(current_user.id)
    return GoogleCalendarListResponse(calendars=calendars)


@router.get(
    "/v1/calendar/family/{family_id}/members/{user_id}/settings",
    response_model=MemberCalendarSettingsResponse,
)
async def get_member_calendar_settings(
    family_id: UUID,
    user_id: UUID,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
):
    """Get a member's shared calendar settings for a family."""
    service = CalendarService(db)
    shared_cals = await service.get_member_settings(family_id, user_id)
    return MemberCalendarSettingsResponse(
        shared_calendars=[
            SharedCalendarResponse(
                id=str(sc.id),
                google_calendar_id=sc.google_calendar_id,
                calendar_name=sc.calendar_name,
                color=sc.color,
                is_enabled=sc.is_enabled,
            )
            for sc in shared_cals
        ]
    )


@router.put(
    "/v1/calendar/family/{family_id}/members/me/settings",
    response_model=MemberCalendarSettingsResponse,
)
async def update_member_calendar_settings(
    family_id: UUID,
    body: MemberCalendarSettingsUpdate,
    member: FamilyMember = Depends(RequireFamilyMember()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current member's shared calendar settings for a family."""
    service = CalendarService(db)
    shared_cals = await service.update_member_settings(
        family_id,
        current_user.id,
        [cal.model_dump() for cal in body.shared_calendars],
    )
    return MemberCalendarSettingsResponse(
        shared_calendars=[
            SharedCalendarResponse(
                id=str(sc.id),
                google_calendar_id=sc.google_calendar_id,
                calendar_name=sc.calendar_name,
                color=sc.color,
                is_enabled=sc.is_enabled,
            )
            for sc in shared_cals
        ]
    )
