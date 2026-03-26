from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.models.family_member import FamilyMember
from app.models.notification import Notification, NotificationType
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.push_service import PushService

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def notify_user(
        self,
        user_id: UUID,
        family_id: UUID,
        type: NotificationType,
        title: str,
        body: str,
        url: str | None = None,
    ) -> Notification:
        """Persist a notification for a single user and send push."""
        notif = Notification(
            user_id=user_id,
            family_id=family_id,
            type=type,
            title=title,
            body=body,
            url=url,
        )
        self.db.add(notif)
        await self.db.commit()
        await self.db.refresh(notif)

        # Fire push (best-effort)
        try:
            push = PushService(self.db)
            await push.send_to_user(user_id, title, body, url)
        except Exception:
            logger.warning("Push failed for notification %s", notif.id, exc_info=True)

        return notif

    async def notify_family(
        self,
        family_id: UUID,
        type: NotificationType,
        title: str,
        body: str,
        url: str | None = None,
        exclude_user_id: UUID | None = None,
    ) -> list[Notification]:
        """Create one notification per family member (excl. actor) and send push."""
        query = select(FamilyMember.user_id).where(
            FamilyMember.family_id == family_id,
        )
        if exclude_user_id:
            query = query.where(FamilyMember.user_id != exclude_user_id)

        result = await self.db.execute(query)
        user_ids = result.scalars().all()

        notifications = []
        for uid in user_ids:
            notif = Notification(
                user_id=uid,
                family_id=family_id,
                type=type,
                title=title,
                body=body,
                url=url,
            )
            self.db.add(notif)
            notifications.append(notif)

        if notifications:
            await self.db.commit()
            for notif in notifications:
                await self.db.refresh(notif)

        # Fire push to family (best-effort)
        try:
            push = PushService(self.db)
            await push.send_to_family(family_id, title, body, url, exclude_user_id)
        except Exception:
            logger.warning("Push to family failed", exc_info=True)

        return notifications

    async def get_inbox(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> NotificationListResponse:
        """Return non-dismissed notifications for a user, newest first."""
        base_filter = [
            Notification.user_id == user_id,
            Notification.dismissed_at.is_(None),
        ]

        # Get notifications page
        result = await self.db.execute(
            select(Notification)
            .where(*base_filter)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        notifications = result.scalars().all()

        # Get counts
        total = await self.db.scalar(
            select(func.count()).select_from(Notification).where(*base_filter)
        )
        unread = await self.db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(*base_filter, Notification.is_read.is_(False))
        )

        return NotificationListResponse(
            notifications=[
                NotificationResponse(
                    id=n.id,
                    type=n.type,
                    title=n.title,
                    body=n.body,
                    url=n.url,
                    is_read=n.is_read,
                    created_at=n.created_at,
                )
                for n in notifications
            ],
            unread_count=unread or 0,
            total_count=total or 0,
        )

    async def get_unread_count(self, user_id: UUID) -> int:
        """Count unread, non-dismissed notifications."""
        count = await self.db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.dismissed_at.is_(None),
                Notification.is_read.is_(False),
            )
        )
        return count or 0

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> bool:
        """Mark a single notification as read. Returns True if found."""
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_read(self, user_id: UUID) -> int:
        """Mark all unread notifications as read. Returns count updated."""
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
                Notification.dismissed_at.is_(None),
            )
            .values(is_read=True)
        )
        await self.db.commit()
        return result.rowcount

    async def dismiss(self, user_id: UUID, notification_id: UUID) -> bool:
        """Dismiss a notification (soft-delete). Returns True if found."""
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(dismissed_at=datetime.now(UTC))
        )
        await self.db.commit()
        return result.rowcount > 0


async def notify_in_background(
    user_id: UUID | None = None,
    family_id: UUID | None = None,
    type: NotificationType = NotificationType.TASK_ASSIGNED,
    title: str = "",
    body: str = "",
    url: str | None = None,
    exclude_user_id: UUID | None = None,
) -> None:
    """Fire-and-forget notification helper.

    Creates its own DB session to avoid reusing a closed request-scoped session.
    Call with asyncio.create_task() from endpoint handlers.
    """
    if not settings.VAPID_PRIVATE_KEY:
        return
    try:
        async with async_session_factory() as db:
            service = NotificationService(db)
            if user_id and family_id:
                await service.notify_user(user_id, family_id, type, title, body, url)
            elif family_id:
                await service.notify_family(
                    family_id, type, title, body, url, exclude_user_id
                )
    except Exception:
        logger.warning("Background notification failed", exc_info=True)
