from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import ALGORITHM, create_access_token, hash_password
from app.models import User
from app.models.google_oauth import GoogleOAuthCredential

pytestmark = pytest.mark.anyio


# --- Helpers ---


async def create_family_with_member(client: AsyncClient, auth_headers: dict) -> str:
    resp = await client.post(
        "/v1/families", json={"name": "Calendar Test Family"}, headers=auth_headers
    )
    return resp.json()["id"]


def make_oauth_state(user_id: str, expired: bool = False) -> str:
    exp = datetime.now(UTC) + (timedelta(minutes=-5) if expired else timedelta(minutes=10))
    return jwt.encode(
        {"sub": user_id, "type": "google_oauth", "exp": exp},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


# --- Auth redirect ---


async def test_google_auth_redirect(client: AsyncClient, test_user: User):
    token, _ = create_access_token(test_user.id)
    resp = await client.get(
        "/v1/calendar/auth/google",
        params={"token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "accounts.google.com" in resp.headers["location"]
    assert "calendar.readonly" in resp.headers["location"]


async def test_google_auth_redirect_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/v1/calendar/auth/google",
        params={"token": "invalid-token"},
        follow_redirects=False,
    )
    assert resp.status_code == 401


# --- Auth callback ---


@patch("app.services.calendar_service.httpx.AsyncClient")
async def test_google_auth_callback_success(
    mock_httpx_cls, client: AsyncClient, test_user: User, db: AsyncSession
):
    # Mock the token exchange
    mock_httpx_instance = AsyncMock()
    mock_httpx_instance.__aenter__ = AsyncMock(return_value=mock_httpx_instance)
    mock_httpx_instance.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_instance.post = AsyncMock(
        return_value=AsyncMock(
            status_code=200,
            json=lambda: {
                "access_token": "fake-access-token",
                "refresh_token": "fake-refresh-token",
                "expires_in": 3600,
            },
        )
    )
    mock_httpx_cls.return_value = mock_httpx_instance

    state = make_oauth_state(str(test_user.id))
    resp = await client.get(
        "/v1/calendar/auth/google/callback",
        params={"code": "fake-auth-code", "state": state},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "google_connected=true" in resp.headers["location"]

    # Verify credential was stored
    from sqlalchemy import select

    result = await db.execute(
        select(GoogleOAuthCredential).where(GoogleOAuthCredential.user_id == test_user.id)
    )
    cred = result.scalar_one_or_none()
    assert cred is not None
    assert cred.scope == "https://www.googleapis.com/auth/calendar.readonly"


async def test_google_auth_callback_invalid_state(client: AsyncClient):
    resp = await client.get(
        "/v1/calendar/auth/google/callback",
        params={"code": "fake-code", "state": "invalid-jwt"},
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert "Invalid" in resp.json()["detail"]


async def test_google_auth_callback_expired_state(client: AsyncClient, test_user: User):
    state = make_oauth_state(str(test_user.id), expired=True)
    resp = await client.get(
        "/v1/calendar/auth/google/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )
    assert resp.status_code == 400


# --- Status ---


async def test_google_status_not_connected(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/v1/calendar/auth/google/status",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["connected"] is False
    assert resp.json()["scope"] is None


@patch("app.services.calendar_service.httpx.AsyncClient")
async def test_google_status_connected(
    mock_httpx_cls, client: AsyncClient, auth_headers: dict, test_user: User, db: AsyncSession
):
    # First connect via callback
    mock_httpx_instance = AsyncMock()
    mock_httpx_instance.__aenter__ = AsyncMock(return_value=mock_httpx_instance)
    mock_httpx_instance.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_instance.post = AsyncMock(
        return_value=AsyncMock(
            status_code=200,
            json=lambda: {
                "access_token": "fake-access-token",
                "refresh_token": "fake-refresh-token",
                "expires_in": 3600,
            },
        )
    )
    mock_httpx_cls.return_value = mock_httpx_instance

    state = make_oauth_state(str(test_user.id))
    await client.get(
        "/v1/calendar/auth/google/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )

    resp = await client.get(
        "/v1/calendar/auth/google/status",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["connected"] is True


# --- Disconnect ---


@patch("app.services.calendar_service.httpx.AsyncClient")
async def test_disconnect_google(
    mock_httpx_cls, client: AsyncClient, auth_headers: dict, test_user: User, db: AsyncSession
):
    # Connect first
    mock_httpx_instance = AsyncMock()
    mock_httpx_instance.__aenter__ = AsyncMock(return_value=mock_httpx_instance)
    mock_httpx_instance.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_instance.post = AsyncMock(
        return_value=AsyncMock(
            status_code=200,
            json=lambda: {
                "access_token": "fake-access-token",
                "refresh_token": "fake-refresh-token",
                "expires_in": 3600,
            },
        )
    )
    mock_httpx_cls.return_value = mock_httpx_instance

    state = make_oauth_state(str(test_user.id))
    await client.get(
        "/v1/calendar/auth/google/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )

    # Disconnect
    resp = await client.delete(
        "/v1/calendar/auth/google",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "disconnected" in resp.json()["message"].lower()

    # Verify disconnected
    resp2 = await client.get(
        "/v1/calendar/auth/google/status",
        headers=auth_headers,
    )
    assert resp2.json()["connected"] is False


# --- Family events ---


async def test_family_events_non_member(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    fid = await create_family_with_member(client, auth_headers)

    # Create second user who is not a member
    user2 = User(
        email="cal_other@example.com",
        username="calother",
        password_hash=hash_password("password123"),
    )
    db.add(user2)
    await db.commit()
    await db.refresh(user2)
    token2, _ = create_access_token(user2.id)
    headers2 = {"Authorization": f"Bearer {token2}"}

    resp = await client.get(
        f"/v1/calendar/family/{fid}/events",
        params={
            "start": "2026-03-01T00:00:00Z",
            "end": "2026-03-31T23:59:59Z",
        },
        headers=headers2,
    )
    assert resp.status_code == 403


async def test_family_events_no_connected_members(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.get(
        f"/v1/calendar/family/{fid}/events",
        params={
            "start": "2026-03-01T00:00:00Z",
            "end": "2026-03-31T23:59:59Z",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] == []
    assert data["connected_members"] == 0
    assert data["total_members"] == 1
