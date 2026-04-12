import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.permissions import RequireFamilyMember
from app.core.pubsub import subscribe_schedule
from app.core.security import JWTError, decode_token, is_token_blacklisted
from app.database import get_db
from app.models import FamilyMember, User
from app.schemas import MessageResponse
from app.schemas.schedules import (
    BulkCreateEventsRequest,
    CreateScheduleRequest,
    EventResponse,
    ScheduleDetailResponse,
    ScheduleResponse,
    UpdateEventRequest,
    UpdateScheduleRequest,
)
from app.services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["schedules"])


# --- Family-scoped schedule endpoints ---


@router.post(
    "/v1/families/{family_id}/schedules",
    response_model=ScheduleResponse,
    status_code=201,
)
async def create_schedule(
    family_id: UUID,
    data: CreateScheduleRequest,
    member: FamilyMember = Depends(RequireFamilyMember()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    return await service.create_schedule(family_id, data, member, current_user)


@router.get(
    "/v1/families/{family_id}/schedules",
    response_model=list[ScheduleResponse],
)
async def get_schedules(
    family_id: UUID,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
):
    service = ScheduleService(db)
    return await service.get_schedules(family_id, member)


# --- Schedule-scoped endpoints ---


@router.get(
    "/v1/families/{family_id}/schedules/{schedule_id}",
    response_model=ScheduleDetailResponse,
)
async def get_schedule_detail(
    schedule_id: UUID,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
):
    service = ScheduleService(db)
    return await service.get_schedule_detail(schedule_id, member)


@router.patch(
    "/v1/families/{family_id}/schedules/{schedule_id}",
    response_model=ScheduleResponse,
)
async def update_schedule(
    schedule_id: UUID,
    data: UpdateScheduleRequest,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
):
    service = ScheduleService(db)
    return await service.update_schedule(schedule_id, data, member)


# --- Event endpoints ---


@router.post(
    "/v1/families/{family_id}/schedules/{schedule_id}/events",
    response_model=list[EventResponse],
    status_code=201,
)
async def add_events(
    schedule_id: UUID,
    data: BulkCreateEventsRequest,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
):
    service = ScheduleService(db)
    return await service.bulk_add_events(schedule_id, data, member)


@router.patch(
    "/v1/families/{family_id}/schedules/{schedule_id}/events/{event_id}",
    response_model=EventResponse,
)
async def update_event(
    schedule_id: UUID,
    event_id: UUID,
    data: UpdateEventRequest,
    member: FamilyMember = Depends(RequireFamilyMember()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
):
    service = ScheduleService(db)
    return await service.update_event(
        schedule_id, event_id, data, member, current_user
    )


@router.delete(
    "/v1/families/{family_id}/schedules/{schedule_id}/events/{event_id}",
    response_model=MessageResponse,
)
async def delete_event(
    schedule_id: UUID,
    event_id: UUID,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
):
    service = ScheduleService(db)
    await service.delete_event(schedule_id, event_id, member)
    return MessageResponse(message="Event deleted")


# --- SSE stream endpoint ---

HEARTBEAT_INTERVAL = 30


@router.get("/v1/families/{family_id}/schedules/{schedule_id}/stream")
async def stream_schedule_events(
    family_id: UUID,
    schedule_id: UUID,
    request: Request,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """SSE endpoint for real-time schedule updates."""
    try:
        payload = decode_token(token)
    except JWTError:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("type") != "access":
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Token revoked")

    user_id = payload.get("sub")
    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == UUID(user_id),
        )
    )
    if not result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not a member of this family")

    async def event_generator():
        pubsub = None
        redis_conn = None
        try:
            pubsub, redis_conn = await subscribe_schedule(schedule_id)

            while True:
                if await request.is_disconnected():
                    break

                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(
                            ignore_subscribe_messages=True, timeout=1.0
                        ),
                        timeout=HEARTBEAT_INTERVAL,
                    )
                except TimeoutError:
                    yield ": heartbeat\n\n"
                    continue

                if message and message["type"] == "message":
                    data = message["data"]
                    try:
                        parsed = json.loads(data)
                        event_type = parsed.get("event", "update")
                        yield f"event: {event_type}\ndata: {data}\n\n"
                    except (json.JSONDecodeError, TypeError):
                        yield f"event: update\ndata: {data}\n\n"
        except Exception:
            logger.warning(
                "SSE stream error for schedule %s", schedule_id, exc_info=True
            )
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(f"schedule:{schedule_id}")
                    await pubsub.aclose()
                except Exception:
                    pass
            if redis_conn:
                try:
                    await redis_conn.aclose()
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
