import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import ALGORITHM, create_access_token, hash_password
from app.models import User
from app.models.family import Family
from app.models.family_member import FamilyMember, FamilyRole
from app.models.google_oauth import GoogleOAuthCredential
from app.services.calendar_service import CalendarService

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


# --- Service-level: _refresh_token_if_needed ---


def _make_fernet():
    return Fernet(settings.FERNET_KEY.encode())


async def _create_cred(db: AsyncSession, user: User, *, expired: bool = False) -> GoogleOAuthCredential:
    """Helper to create a GoogleOAuthCredential in the DB.

    Note: we skip db.refresh() because expire_on_commit=False keeps Python
    values (including timezone-aware datetimes) intact, avoiding the SQLite
    naive-datetime round-trip issue.
    """
    fernet = _make_fernet()
    if expired:
        expiry = datetime.now(UTC) - timedelta(hours=1)
    else:
        expiry = datetime.now(UTC) + timedelta(hours=1)
    cred = GoogleOAuthCredential(
        user_id=user.id,
        encrypted_access_token=fernet.encrypt(b"fake-access-token").decode(),
        encrypted_refresh_token=fernet.encrypt(b"fake-refresh-token").decode(),
        token_expiry=expiry,
        scope="https://www.googleapis.com/auth/calendar.readonly",
    )
    db.add(cred)
    await db.commit()
    return cred


async def test_refresh_token_not_expired_returns_cached(
    db: AsyncSession, test_user: User
):
    """Token not expired: returns decrypted access_token without any HTTP call."""
    cred = await _create_cred(db, test_user, expired=False)
    svc = CalendarService(db)

    with patch("app.services.calendar_service.httpx.AsyncClient") as mock_httpx_cls:
        result = await svc._refresh_token_if_needed(cred)

    # Should NOT have created an HTTP client at all
    mock_httpx_cls.assert_not_called()
    assert result == "fake-access-token"


@patch("app.services.calendar_service.httpx.AsyncClient")
async def test_refresh_token_expired_refreshes(
    mock_httpx_cls, db: AsyncSession, test_user: User
):
    """Token expired: refreshes via Google, updates DB with new token and expiry."""
    cred = await _create_cred(db, test_user, expired=True)
    old_expiry = cred.token_expiry
    svc = CalendarService(db)

    mock_httpx_instance = AsyncMock()
    mock_httpx_instance.__aenter__ = AsyncMock(return_value=mock_httpx_instance)
    mock_httpx_instance.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_instance.post = AsyncMock(
        return_value=AsyncMock(
            status_code=200,
            json=lambda: {
                "access_token": "new-access-token",
                "expires_in": 7200,
            },
        )
    )
    mock_httpx_cls.return_value = mock_httpx_instance

    result = await svc._refresh_token_if_needed(cred)

    assert result == "new-access-token"
    # DB should be updated
    fernet = _make_fernet()
    assert fernet.decrypt(cred.encrypted_access_token.encode()).decode() == "new-access-token"
    assert cred.token_expiry > old_expiry
    mock_httpx_instance.post.assert_called_once()


@patch("app.services.calendar_service.httpx.AsyncClient")
async def test_refresh_token_failure(
    mock_httpx_cls, db: AsyncSession, test_user: User
):
    """Token expired + Google returns non-200: raises RuntimeError."""
    cred = await _create_cred(db, test_user, expired=True)
    svc = CalendarService(db)

    mock_httpx_instance = AsyncMock()
    mock_httpx_instance.__aenter__ = AsyncMock(return_value=mock_httpx_instance)
    mock_httpx_instance.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_instance.post = AsyncMock(
        return_value=AsyncMock(
            status_code=400,
            text="invalid_grant",
        )
    )
    mock_httpx_cls.return_value = mock_httpx_instance

    with pytest.raises(RuntimeError, match="Failed to refresh Google token"):
        await svc._refresh_token_if_needed(cred)


# --- Service-level: _fetch_member_events ---


def _mock_httpx_for_calendar(calendar_items: list[dict]) -> tuple:
    """Build mock httpx client that returns calendar items on GET."""
    mock_httpx_instance = AsyncMock()
    mock_httpx_instance.__aenter__ = AsyncMock(return_value=mock_httpx_instance)
    mock_httpx_instance.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_instance.get = AsyncMock(
        return_value=AsyncMock(
            status_code=200,
            json=lambda: {"items": calendar_items},
            raise_for_status=lambda: None,
        )
    )
    # Also mock POST for _refresh_token_if_needed (won't be called if token not expired)
    mock_httpx_instance.post = AsyncMock()
    return mock_httpx_instance


@patch("app.services.calendar_service.httpx.AsyncClient")
async def test_fetch_member_events_success(
    mock_httpx_cls, db: AsyncSession, test_user: User
):
    """Successful event fetch with dateTime-based events."""
    cred = await _create_cred(db, test_user, expired=False)
    svc = CalendarService(db)

    items = [
        {
            "id": "evt1",
            "summary": "Team Meeting",
            "start": {"dateTime": "2026-03-10T09:00:00Z"},
            "end": {"dateTime": "2026-03-10T10:00:00Z"},
        },
        {
            "id": "evt2",
            "summary": "Lunch",
            "start": {"dateTime": "2026-03-10T12:00:00Z"},
            "end": {"dateTime": "2026-03-10T13:00:00Z"},
        },
    ]
    mock_httpx_cls.return_value = _mock_httpx_for_calendar(items)

    start = datetime(2026, 3, 1, tzinfo=UTC)
    end = datetime(2026, 3, 31, tzinfo=UTC)
    events = await svc._fetch_member_events(cred, start, end)

    assert len(events) == 2
    assert events[0]["id"] == "evt1"
    assert events[0]["title"] == "Team Meeting"
    assert events[0]["start"] == "2026-03-10T09:00:00Z"
    assert events[0]["all_day"] is False
    assert events[1]["id"] == "evt2"


@patch("app.services.calendar_service.httpx.AsyncClient")
async def test_fetch_member_events_all_day(
    mock_httpx_cls, db: AsyncSession, test_user: User
):
    """All-day event uses 'date' not 'dateTime', all_day flag is True."""
    cred = await _create_cred(db, test_user, expired=False)
    svc = CalendarService(db)

    items = [
        {
            "id": "allday1",
            "summary": "Holiday",
            "start": {"date": "2026-03-15"},
            "end": {"date": "2026-03-16"},
        },
    ]
    mock_httpx_cls.return_value = _mock_httpx_for_calendar(items)

    start = datetime(2026, 3, 1, tzinfo=UTC)
    end = datetime(2026, 3, 31, tzinfo=UTC)
    events = await svc._fetch_member_events(cred, start, end)

    assert len(events) == 1
    assert events[0]["all_day"] is True
    assert events[0]["start"] == "2026-03-15"
    assert events[0]["end"] == "2026-03-16"
    assert events[0]["title"] == "Holiday"


@patch("app.services.calendar_service.httpx.AsyncClient")
async def test_fetch_member_events_no_title(
    mock_httpx_cls, db: AsyncSession, test_user: User
):
    """Event missing 'summary' defaults to '(No title)'."""
    cred = await _create_cred(db, test_user, expired=False)
    svc = CalendarService(db)

    items = [
        {
            "id": "notitle1",
            "start": {"dateTime": "2026-03-10T14:00:00Z"},
            "end": {"dateTime": "2026-03-10T15:00:00Z"},
        },
    ]
    mock_httpx_cls.return_value = _mock_httpx_for_calendar(items)

    start = datetime(2026, 3, 1, tzinfo=UTC)
    end = datetime(2026, 3, 31, tzinfo=UTC)
    events = await svc._fetch_member_events(cred, start, end)

    assert len(events) == 1
    assert events[0]["title"] == "(No title)"


# --- Service-level: get_family_events partial failure & cache ---


@patch("app.services.calendar_service.httpx.AsyncClient")
async def test_family_events_partial_failure(
    mock_httpx_cls, db: AsyncSession, test_user: User
):
    """One member's fetch fails, the other succeeds: failed member is skipped."""
    # Create family + two members with credentials
    family = Family(name="Partial Fail Family")
    db.add(family)
    await db.commit()
    await db.refresh(family)

    member1 = FamilyMember(
        family_id=family.id, user_id=test_user.id, role=FamilyRole.PARENT, is_admin=True
    )
    db.add(member1)

    user2 = User(
        email="member2@example.com",
        username="member2",
        password_hash=hash_password("password123"),
    )
    db.add(user2)
    await db.commit()
    await db.refresh(user2)

    member2 = FamilyMember(
        family_id=family.id, user_id=user2.id, role=FamilyRole.PARENT, is_admin=False
    )
    db.add(member2)
    await db.commit()

    # Create OAuth creds for both
    cred1 = await _create_cred(db, test_user, expired=False)
    fernet = _make_fernet()
    cred2 = GoogleOAuthCredential(
        user_id=user2.id,
        encrypted_access_token=fernet.encrypt(b"token2").decode(),
        encrypted_refresh_token=fernet.encrypt(b"refresh2").decode(),
        token_expiry=datetime.now(UTC) + timedelta(hours=1),
        scope="https://www.googleapis.com/auth/calendar.readonly",
    )
    db.add(cred2)
    await db.commit()

    svc = CalendarService(db)

    call_count = 0

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First member succeeds
            return AsyncMock(
                status_code=200,
                json=lambda: {
                    "items": [
                        {
                            "id": "evt_ok",
                            "summary": "Good Event",
                            "start": {"dateTime": "2026-03-10T09:00:00Z"},
                            "end": {"dateTime": "2026-03-10T10:00:00Z"},
                        }
                    ]
                },
                raise_for_status=lambda: None,
            )
        else:
            # Second member fails
            raise RuntimeError("Simulated Google API failure")

    mock_httpx_instance = AsyncMock()
    mock_httpx_instance.__aenter__ = AsyncMock(return_value=mock_httpx_instance)
    mock_httpx_instance.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_instance.get = mock_get
    mock_httpx_cls.return_value = mock_httpx_instance

    start = datetime(2026, 3, 1, tzinfo=UTC)
    end = datetime(2026, 3, 31, tzinfo=UTC)
    result = await svc.get_family_events(family.id, start, end)

    # Should have 1 event from the member that succeeded
    assert len(result["events"]) == 1
    assert result["events"][0]["title"] == "Good Event"
    assert result["connected_members"] == 2
    assert result["total_members"] == 2


async def test_family_events_cached(db: AsyncSession, test_user: User):
    """Pre-populated redis cache returns data without any HTTP calls."""
    # Create family + member
    family = Family(name="Cached Family")
    db.add(family)
    await db.commit()
    await db.refresh(family)

    member = FamilyMember(
        family_id=family.id, user_id=test_user.id, role=FamilyRole.PARENT, is_admin=True
    )
    db.add(member)
    await db.commit()

    svc = CalendarService(db)

    start = datetime(2026, 3, 1, tzinfo=UTC)
    end = datetime(2026, 3, 31, tzinfo=UTC)

    # Pre-populate the redis cache
    from app.core.redis import get_redis

    redis = await get_redis()
    cache_key = f"calendar:{family.id}:{start.isoformat()}:{end.isoformat()}"
    cached_data = {
        "events": [
            {
                "id": "cached_evt",
                "title": "Cached Event",
                "start": "2026-03-10T09:00:00Z",
                "end": "2026-03-10T10:00:00Z",
                "all_day": False,
                "member_name": "testuser",
                "color": "#4F46E5",
            }
        ],
        "connected_members": 1,
        "total_members": 1,
    }
    await redis.setex(cache_key, 300, json.dumps(cached_data))

    with patch("app.services.calendar_service.httpx.AsyncClient") as mock_httpx_cls:
        result = await svc.get_family_events(family.id, start, end)

    # No HTTP calls should have been made
    mock_httpx_cls.assert_not_called()
    assert len(result["events"]) == 1
    assert result["events"][0]["title"] == "Cached Event"
    assert result["connected_members"] == 1
