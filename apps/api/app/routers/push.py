import base64

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, load_der_public_key
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.push import (
    PushSubscribeRequest,
    PushSubscriptionResponse,
    PushUnsubscribeRequest,
    VapidKeyResponse,
)
from app.services.push_service import PushService

router = APIRouter(tags=["push"])


@router.get("/v1/push/vapid-key", response_model=VapidKeyResponse)
async def get_vapid_key(
    current_user: User = Depends(get_current_user),
) -> VapidKeyResponse:
    """Return the public VAPID key for push subscription."""
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications not configured",
        )
    # Convert SPKI/DER-encoded key to raw 65-byte uncompressed EC point
    # (Web Push API requires the raw key, not the SPKI wrapper)
    raw_key = settings.VAPID_PUBLIC_KEY
    try:
        der_bytes = base64.b64decode(raw_key + "=" * (-len(raw_key) % 4))
        if len(der_bytes) == 91:
            # SPKI-encoded: extract raw 65-byte uncompressed point
            pub = load_der_public_key(der_bytes)
            raw_bytes = pub.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
            raw_key = base64.urlsafe_b64encode(raw_bytes).decode().rstrip("=")
    except Exception:
        pass  # Return as-is if already in correct format

    return VapidKeyResponse(public_key=raw_key)


@router.post(
    "/v1/push/subscribe",
    response_model=PushSubscriptionResponse,
    status_code=201,
)
async def subscribe(
    data: PushSubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PushSubscriptionResponse:
    """Register a push subscription for the current user."""
    service = PushService(db)
    sub = await service.subscribe(
        user_id=current_user.id,
        endpoint=data.endpoint,
        p256dh=data.keys.p256dh,
        auth=data.keys.auth,
    )
    return PushSubscriptionResponse(
        id=sub.id,
        endpoint=sub.endpoint,
        created_at=sub.created_at,
    )


@router.delete("/v1/push/subscribe", status_code=204)
async def unsubscribe(
    data: PushUnsubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a push subscription for the current user."""
    service = PushService(db)
    await service.unsubscribe(
        user_id=current_user.id,
        endpoint=data.endpoint,
    )
