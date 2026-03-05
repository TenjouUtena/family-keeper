"""Tests for push notification endpoints and service."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models.push_subscription import PushSubscription
from app.services.push_service import PushService

# --- Endpoint tests ---


@pytest.mark.asyncio
async def test_get_vapid_key(client: AsyncClient, auth_headers: dict):
    """GET /v1/push/vapid-key returns public key when configured."""
    with patch("app.routers.push.settings") as mock_settings:
        mock_settings.VAPID_PUBLIC_KEY = "test-vapid-public-key"
        resp = await client.get("/v1/push/vapid-key", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["public_key"] == "test-vapid-public-key"


@pytest.mark.asyncio
async def test_get_vapid_key_not_configured(client: AsyncClient, auth_headers: dict):
    """GET /v1/push/vapid-key returns 503 when not configured."""
    with patch("app.routers.push.settings") as mock_settings:
        mock_settings.VAPID_PUBLIC_KEY = ""
        resp = await client.get("/v1/push/vapid-key", headers=auth_headers)
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_get_vapid_key_unauthenticated(client: AsyncClient):
    """GET /v1/push/vapid-key requires auth."""
    resp = await client.get("/v1/push/vapid-key")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_subscribe(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """POST /v1/push/subscribe registers a subscription."""
    resp = await client.post(
        "/v1/push/subscribe",
        headers=auth_headers,
        json={
            "endpoint": "https://push.example.com/sub1",
            "keys": {"p256dh": "test-p256dh-key", "auth": "test-auth-key"},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["endpoint"] == "https://push.example.com/sub1"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_subscribe_duplicate_updates(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    """POST /v1/push/subscribe with same endpoint updates existing."""
    payload = {
        "endpoint": "https://push.example.com/sub-dup",
        "keys": {"p256dh": "key1", "auth": "auth1"},
    }
    resp1 = await client.post("/v1/push/subscribe", headers=auth_headers, json=payload)
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    # Subscribe again with same endpoint but different keys
    payload["keys"] = {"p256dh": "key2", "auth": "auth2"}
    resp2 = await client.post("/v1/push/subscribe", headers=auth_headers, json=payload)
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    # Should be the same subscription (updated, not duplicated)
    assert id1 == id2


@pytest.mark.asyncio
async def test_unsubscribe(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """DELETE /v1/push/subscribe removes subscription."""
    # First subscribe
    await client.post(
        "/v1/push/subscribe",
        headers=auth_headers,
        json={
            "endpoint": "https://push.example.com/sub-del",
            "keys": {"p256dh": "p256dh", "auth": "auth"},
        },
    )

    # Then unsubscribe
    resp = await client.request(
        "DELETE",
        "/v1/push/subscribe",
        headers=auth_headers,
        json={"endpoint": "https://push.example.com/sub-del"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_subscribe_unauthenticated(client: AsyncClient):
    """POST /v1/push/subscribe requires auth."""
    resp = await client.post(
        "/v1/push/subscribe",
        json={
            "endpoint": "https://push.example.com/sub",
            "keys": {"p256dh": "key", "auth": "auth"},
        },
    )
    assert resp.status_code == 403


# --- Service tests ---


@pytest.mark.asyncio
async def test_push_service_subscribe(db: AsyncSession, test_user: User):
    """PushService.subscribe creates a subscription."""
    service = PushService(db)
    sub = await service.subscribe(
        user_id=test_user.id,
        endpoint="https://push.example.com/svc",
        p256dh="p256dh-val",
        auth="auth-val",
    )
    assert sub.endpoint == "https://push.example.com/svc"
    assert sub.user_id == test_user.id


@pytest.mark.asyncio
async def test_push_service_unsubscribe(db: AsyncSession, test_user: User):
    """PushService.unsubscribe removes a subscription."""
    service = PushService(db)
    await service.subscribe(
        user_id=test_user.id,
        endpoint="https://push.example.com/unsub",
        p256dh="p256dh",
        auth="auth",
    )
    await service.unsubscribe(test_user.id, "https://push.example.com/unsub")

    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == test_user.id,
            PushSubscription.endpoint == "https://push.example.com/unsub",
        )
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_push_service_send_skips_when_no_vapid(db: AsyncSession, test_user: User):
    """send_to_user does nothing when VAPID key not configured."""
    service = PushService(db)
    await service.subscribe(
        user_id=test_user.id,
        endpoint="https://push.example.com/nop",
        p256dh="p256dh",
        auth="auth",
    )

    with patch("app.services.push_service.settings") as mock_settings:
        mock_settings.VAPID_PRIVATE_KEY = ""
        with patch("app.services.push_service.webpush") as mock_webpush:
            await service.send_to_user(test_user.id, "Title", "Body")
            mock_webpush.assert_not_called()


@pytest.mark.asyncio
async def test_push_service_send_calls_webpush(db: AsyncSession, test_user: User):
    """send_to_user calls pywebpush for each subscription."""
    service = PushService(db)
    await service.subscribe(
        user_id=test_user.id,
        endpoint="https://push.example.com/send",
        p256dh="p256dh",
        auth="auth",
    )

    with patch("app.services.push_service.settings") as mock_settings:
        mock_settings.VAPID_PRIVATE_KEY = "fake-private-key"
        mock_settings.VAPID_MAILTO = "mailto:test@example.com"
        with patch("app.services.push_service.webpush") as mock_webpush:
            await service.send_to_user(test_user.id, "Test Title", "Test Body")
            mock_webpush.assert_called_once()
            call_kwargs = mock_webpush.call_args
            assert call_kwargs[1]["subscription_info"]["endpoint"] == "https://push.example.com/send"


@pytest.mark.asyncio
async def test_push_service_cleans_stale_410(db: AsyncSession, test_user: User):
    """send_to_user removes subscriptions that return 410 Gone."""
    from pywebpush import WebPushException

    service = PushService(db)
    sub = await service.subscribe(
        user_id=test_user.id,
        endpoint="https://push.example.com/stale",
        p256dh="p256dh",
        auth="auth",
    )

    mock_response = MagicMock()
    mock_response.status_code = 410

    with patch("app.services.push_service.settings") as mock_settings:
        mock_settings.VAPID_PRIVATE_KEY = "fake-private-key"
        mock_settings.VAPID_MAILTO = "mailto:test@example.com"
        with patch(
            "app.services.push_service.webpush",
            side_effect=WebPushException("Gone", response=mock_response),
        ):
            await service.send_to_user(test_user.id, "Title", "Body")

    # Subscription should be cleaned up
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.id == sub.id)
    )
    assert result.scalar_one_or_none() is None
