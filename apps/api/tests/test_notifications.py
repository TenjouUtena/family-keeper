"""Tests for notification endpoints and service."""

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import Family, FamilyMember, User
from app.models.notification import Notification, NotificationType
from app.services.notification_service import NotificationService

# --- Helpers ---


async def _create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    family_id: uuid.UUID,
    *,
    type: str = NotificationType.TASK_ASSIGNED,
    title: str = "Chores",
    body: str = '"Take out trash" assigned to you',
    url: str | None = "/families/123/lists/456",
    is_read: bool = False,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        family_id=family_id,
        type=type,
        title=title,
        body=body,
        url=url,
        is_read=is_read,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


# --- Endpoint tests ---


@pytest.mark.asyncio
async def test_list_notifications(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    db: AsyncSession,
):
    family = Family(name="Test Family")
    db.add(family)
    await db.flush()

    await _create_notification(db, test_user.id, family.id, title="First")
    await _create_notification(db, test_user.id, family.id, title="Second")

    resp = await client.get("/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 2
    assert data["unread_count"] == 2
    assert len(data["notifications"]) == 2
    # Newest first
    assert data["notifications"][0]["title"] == "Second"
    assert data["notifications"][1]["title"] == "First"


@pytest.mark.asyncio
async def test_list_notifications_excludes_dismissed(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    db: AsyncSession,
):
    family = Family(name="Test Family")
    db.add(family)
    await db.flush()

    await _create_notification(db, test_user.id, family.id, title="Kept")
    n2 = await _create_notification(db, test_user.id, family.id, title="Dismissed")

    # Dismiss n2
    resp = await client.post(
        f"/v1/notifications/{n2.id}/dismiss", headers=auth_headers
    )
    assert resp.status_code == 204

    resp = await client.get("/v1/notifications", headers=auth_headers)
    data = resp.json()
    assert data["total_count"] == 1
    assert data["notifications"][0]["title"] == "Kept"


@pytest.mark.asyncio
async def test_unread_count(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    db: AsyncSession,
):
    family = Family(name="Test Family")
    db.add(family)
    await db.flush()

    await _create_notification(db, test_user.id, family.id, is_read=False)
    await _create_notification(db, test_user.id, family.id, is_read=True)
    await _create_notification(db, test_user.id, family.id, is_read=False)

    resp = await client.get("/v1/notifications/unread-count", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


@pytest.mark.asyncio
async def test_mark_read(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    db: AsyncSession,
):
    family = Family(name="Test Family")
    db.add(family)
    await db.flush()

    n = await _create_notification(db, test_user.id, family.id)
    assert n.is_read is False

    resp = await client.post(f"/v1/notifications/{n.id}/read", headers=auth_headers)
    assert resp.status_code == 204

    # Verify count went down
    resp = await client.get("/v1/notifications/unread-count", headers=auth_headers)
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_mark_read_not_found(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
):
    resp = await client.post(
        f"/v1/notifications/{uuid.uuid4()}/read", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_all_read(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    db: AsyncSession,
):
    family = Family(name="Test Family")
    db.add(family)
    await db.flush()

    await _create_notification(db, test_user.id, family.id)
    await _create_notification(db, test_user.id, family.id)
    await _create_notification(db, test_user.id, family.id, is_read=True)

    resp = await client.post("/v1/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] == 2  # only 2 were unread

    resp = await client.get("/v1/notifications/unread-count", headers=auth_headers)
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_dismiss(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    db: AsyncSession,
):
    family = Family(name="Test Family")
    db.add(family)
    await db.flush()

    n = await _create_notification(db, test_user.id, family.id)

    resp = await client.post(f"/v1/notifications/{n.id}/dismiss", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/v1/notifications", headers=auth_headers)
    assert resp.json()["total_count"] == 0


@pytest.mark.asyncio
async def test_notifications_unauthenticated(client: AsyncClient):
    resp = await client.get("/v1/notifications")
    assert resp.status_code == 403

    resp = await client.get("/v1/notifications/unread-count")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_pagination(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    db: AsyncSession,
):
    family = Family(name="Test Family")
    db.add(family)
    await db.flush()

    for i in range(5):
        await _create_notification(db, test_user.id, family.id, title=f"N{i}")

    resp = await client.get(
        "/v1/notifications?limit=2&offset=0", headers=auth_headers
    )
    data = resp.json()
    assert len(data["notifications"]) == 2
    assert data["total_count"] == 5

    resp = await client.get(
        "/v1/notifications?limit=2&offset=4", headers=auth_headers
    )
    data = resp.json()
    assert len(data["notifications"]) == 1


# --- Service tests ---


@pytest.mark.asyncio
async def test_notify_user_creates_notification(db: AsyncSession):
    user = User(
        email="svc@example.com",
        username="svcuser",
        password_hash=hash_password("pass"),
    )
    db.add(user)
    family = Family(name="Svc Family")
    db.add(family)
    await db.flush()

    with patch("app.services.notification_service.PushService"):
        service = NotificationService(db)
        notif = await service.notify_user(
            user_id=user.id,
            family_id=family.id,
            type=NotificationType.TASK_ASSIGNED,
            title="Chores",
            body='"Dishes" assigned to you',
            url="/families/x/lists/y",
        )

    assert notif.id is not None
    assert notif.user_id == user.id
    assert notif.type == NotificationType.TASK_ASSIGNED
    assert notif.is_read is False


@pytest.mark.asyncio
async def test_notify_family_creates_per_member_notifications(db: AsyncSession):
    user1 = User(
        email="u1@example.com",
        username="user1",
        password_hash=hash_password("pass"),
    )
    user2 = User(
        email="u2@example.com",
        username="user2",
        password_hash=hash_password("pass"),
    )
    actor = User(
        email="actor@example.com",
        username="actor",
        password_hash=hash_password("pass"),
    )
    db.add_all([user1, user2, actor])
    family = Family(name="Fam")
    db.add(family)
    await db.flush()

    db.add(FamilyMember(family_id=family.id, user_id=user1.id, role="child"))
    db.add(FamilyMember(family_id=family.id, user_id=user2.id, role="child"))
    db.add(FamilyMember(family_id=family.id, user_id=actor.id, role="parent"))
    await db.flush()

    with patch("app.services.notification_service.PushService"):
        service = NotificationService(db)
        notifications = await service.notify_family(
            family_id=family.id,
            type=NotificationType.TASK_COMPLETED,
            title="Chores",
            body='"Dishes" completed',
            exclude_user_id=actor.id,
        )

    assert len(notifications) == 2
    notif_user_ids = {n.user_id for n in notifications}
    assert user1.id in notif_user_ids
    assert user2.id in notif_user_ids
    assert actor.id not in notif_user_ids


@pytest.mark.asyncio
async def test_notify_user_push_failure_still_persists(db: AsyncSession):
    user = User(
        email="fail@example.com",
        username="failuser",
        password_hash=hash_password("pass"),
    )
    db.add(user)
    family = Family(name="Fam")
    db.add(family)
    await db.flush()

    with patch(
        "app.services.notification_service.PushService"
    ) as mock_push:
        mock_push.return_value.send_to_user.side_effect = Exception("Push broke")
        service = NotificationService(db)
        notif = await service.notify_user(
            user_id=user.id,
            family_id=family.id,
            type=NotificationType.TASK_ASSIGNED,
            title="Test",
            body="Test body",
        )

    # Notification still persisted despite push failure
    assert notif.id is not None
    assert notif.user_id == user.id
