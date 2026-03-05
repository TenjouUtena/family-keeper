from __future__ import annotations

import json
import logging
from uuid import UUID

from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.family_member import FamilyMember
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


class PushService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def subscribe(
        self, user_id: UUID, endpoint: str, p256dh: str, auth: str
    ) -> PushSubscription:
        """Register or update a push subscription for a user."""
        # Check for existing subscription with same endpoint
        result = await self.db.execute(
            select(PushSubscription).where(
                PushSubscription.user_id == user_id,
                PushSubscription.endpoint == endpoint,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.p256dh = p256dh
            existing.auth = auth
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        sub = PushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        )
        self.db.add(sub)
        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    async def unsubscribe(self, user_id: UUID, endpoint: str) -> None:
        """Remove a push subscription."""
        await self.db.execute(
            delete(PushSubscription).where(
                PushSubscription.user_id == user_id,
                PushSubscription.endpoint == endpoint,
            )
        )
        await self.db.commit()

    async def send_to_user(
        self,
        user_id: UUID,
        title: str,
        body: str,
        url: str | None = None,
    ) -> None:
        """Send push notification to all subscriptions for a user."""
        result = await self.db.execute(
            select(PushSubscription).where(
                PushSubscription.user_id == user_id
            )
        )
        subscriptions = result.scalars().all()
        await self._send_to_subscriptions(subscriptions, title, body, url)

    async def send_to_family(
        self,
        family_id: UUID,
        title: str,
        body: str,
        url: str | None = None,
        exclude_user_id: UUID | None = None,
    ) -> None:
        """Send push notification to all family members (optionally excluding one)."""
        query = (
            select(PushSubscription)
            .join(FamilyMember, FamilyMember.user_id == PushSubscription.user_id)
            .where(FamilyMember.family_id == family_id)
        )
        if exclude_user_id:
            query = query.where(PushSubscription.user_id != exclude_user_id)

        result = await self.db.execute(query)
        subscriptions = result.scalars().all()
        await self._send_to_subscriptions(subscriptions, title, body, url)

    async def _send_to_subscriptions(
        self,
        subscriptions: list[PushSubscription],
        title: str,
        body: str,
        url: str | None = None,
    ) -> None:
        """Send push to a list of subscriptions, cleaning up stale ones."""
        if not settings.VAPID_PRIVATE_KEY or not subscriptions:
            return

        payload = json.dumps({"title": title, "body": body, "url": url or "/"})
        stale_ids: list = []

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                    },
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={
                        "sub": settings.VAPID_MAILTO,
                    },
                )
            except WebPushException as e:
                if e.response and e.response.status_code == 410:
                    stale_ids.append(sub.id)
                    logger.info("Removing stale push subscription %s", sub.id)
                else:
                    logger.warning(
                        "Push notification failed for subscription %s: %s",
                        sub.id,
                        e,
                    )
            except Exception:
                logger.warning(
                    "Push notification failed for subscription %s",
                    sub.id,
                    exc_info=True,
                )

        # Clean up stale subscriptions
        if stale_ids:
            await self.db.execute(
                delete(PushSubscription).where(
                    PushSubscription.id.in_(stale_ids)
                )
            )
            await self.db.commit()


async def notify_in_background(
    db: AsyncSession,
    user_id: UUID | None = None,
    family_id: UUID | None = None,
    title: str = "",
    body: str = "",
    url: str | None = None,
    exclude_user_id: UUID | None = None,
) -> None:
    """Fire-and-forget push notification helper.

    Call with asyncio.create_task() from endpoint handlers.
    """
    if not settings.VAPID_PRIVATE_KEY:
        return
    try:
        service = PushService(db)
        if user_id:
            await service.send_to_user(user_id, title, body, url)
        elif family_id:
            await service.send_to_family(
                family_id, title, body, url, exclude_user_id
            )
    except Exception:
        logger.warning("Background push notification failed", exc_info=True)
