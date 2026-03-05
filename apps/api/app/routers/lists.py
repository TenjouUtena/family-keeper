import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.permissions import RequireFamilyMember
from app.core.pubsub import subscribe_list
from app.core.security import JWTError, decode_token, is_token_blacklisted
from app.database import get_db
from app.models import FamilyMember, ItemAttachment, User
from app.schemas import MessageResponse
from app.schemas.lists import (
    AttachmentResponse,
    BulkCreateItemsRequest,
    CreateListRequest,
    ItemResponse,
    ListDetailResponse,
    ListResponse,
    ReorderItemsRequest,
    UpdateItemRequest,
    UpdateListRequest,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.list_service import ListService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["lists"])


# --- Family-scoped list endpoints ---


@router.post(
    "/v1/families/{family_id}/lists",
    response_model=ListResponse,
    status_code=201,
)
async def create_list(
    family_id: UUID,
    data: CreateListRequest,
    member: FamilyMember = Depends(RequireFamilyMember()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ListService(db)
    return await service.create_list(family_id, data, member, current_user)


@router.get(
    "/v1/families/{family_id}/lists",
    response_model=list[ListResponse],
)
async def get_lists(
    family_id: UUID,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
):
    service = ListService(db)
    return await service.get_lists(family_id, member)


# --- List-scoped endpoints ---
# These need family_id in the path for RBAC dependency


@router.get(
    "/v1/families/{family_id}/lists/{list_id}",
    response_model=ListDetailResponse,
)
async def get_list_detail(
    list_id: UUID,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,  # consumed by RBAC dependency
):
    service = ListService(db)
    return await service.get_list_detail(list_id, member)


@router.patch(
    "/v1/families/{family_id}/lists/{list_id}",
    response_model=ListResponse,
)
async def update_list(
    list_id: UUID,
    data: UpdateListRequest,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
):
    service = ListService(db)
    return await service.update_list(list_id, data, member)


# --- Item endpoints ---


@router.post(
    "/v1/families/{family_id}/lists/{list_id}/items",
    response_model=list[ItemResponse],
    status_code=201,
)
async def add_items(
    list_id: UUID,
    data: BulkCreateItemsRequest,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
):
    service = ListService(db)
    return await service.bulk_add_items(list_id, data, member)


# reorder must come before {item_id} to avoid path conflict
@router.patch(
    "/v1/families/{family_id}/lists/{list_id}/items/reorder",
    response_model=list[ItemResponse],
)
async def reorder_items(
    list_id: UUID,
    data: ReorderItemsRequest,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
):
    service = ListService(db)
    return await service.reorder_items(list_id, data, member)


@router.patch(
    "/v1/families/{family_id}/lists/{list_id}/items/{item_id}",
    response_model=ItemResponse,
)
async def update_item(
    list_id: UUID,
    item_id: UUID,
    data: UpdateItemRequest,
    member: FamilyMember = Depends(RequireFamilyMember()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
):
    service = ListService(db)
    return await service.update_item(
        list_id, item_id, data, member, current_user
    )


@router.delete(
    "/v1/families/{family_id}/lists/{list_id}/items/{item_id}",
    response_model=MessageResponse,
)
async def delete_item(
    list_id: UUID,
    item_id: UUID,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
):
    service = ListService(db)
    await service.delete_item(list_id, item_id, member)
    return MessageResponse(message="Item deleted")


# --- Attachment endpoints ---


@router.post(
    "/v1/families/{family_id}/lists/{list_id}"
    "/items/{item_id}/attachments/upload-url",
    response_model=UploadUrlResponse,
    status_code=201,
)
async def get_upload_url(
    list_id: UUID,
    item_id: UUID,
    data: UploadUrlRequest,
    member: FamilyMember = Depends(RequireFamilyMember()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
):
    service = StorageService(db)
    result = await service.generate_upload_url(
        list_id=list_id,
        item_id=item_id,
        filename=data.filename,
        mime_type=data.mime_type,
        file_size_bytes=data.file_size_bytes,
        is_completion_photo=data.is_completion_photo,
        member=member,
        user=current_user,
    )
    return UploadUrlResponse(**result)


@router.post(
    "/v1/families/{family_id}/lists/{list_id}"
    "/items/{item_id}/attachments/{attachment_id}/confirm",
    response_model=AttachmentResponse,
)
async def confirm_upload(
    item_id: UUID,
    attachment_id: UUID,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
    list_id: UUID = None,
):
    service = StorageService(db)
    return await service.confirm_upload(item_id, attachment_id, member)


@router.get(
    "/v1/families/{family_id}/lists/{list_id}"
    "/items/{item_id}/attachments/{attachment_id}/url",
)
async def get_attachment_url(
    item_id: UUID,
    attachment_id: UUID,
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
    family_id: UUID = None,
    list_id: UUID = None,
):
    attachment = await db.get(ItemAttachment, attachment_id)
    if not attachment or attachment.item_id != item_id:
        raise HTTPException(
            status_code=404, detail="Attachment not found"
        )
    service = StorageService(db)
    url = await service.get_download_url(attachment.storage_key)
    return {"url": url}


# --- SSE stream endpoint ---

HEARTBEAT_INTERVAL = 30


@router.get("/v1/families/{family_id}/lists/{list_id}/stream")
async def stream_list_events(
    family_id: UUID,
    list_id: UUID,
    request: Request,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """SSE endpoint for real-time list updates.

    Auth via query param because EventSource cannot send headers.
    """
    # Validate token
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        raise HTTPException(status_code=401, detail="Token revoked")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Verify family membership
    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == UUID(user_id),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this family")

    async def event_generator():
        pubsub = None
        redis_conn = None
        try:
            pubsub, redis_conn = await subscribe_list(list_id)

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
                    # Send heartbeat
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
                "SSE stream error for list %s", list_id, exc_info=True
            )
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(f"list:{list_id}")
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
