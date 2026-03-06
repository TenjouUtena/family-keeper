from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services.auth_service import AuthService


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        res = await client.post(
            "/v1/auth/register",
            json={"email": "new@example.com", "username": "newuser", "password": "password123"},
        )
        assert res.status_code == 201
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        res = await client.post(
            "/v1/auth/register",
            json={"email": "test@example.com", "username": "other", "password": "password123"},
        )
        assert res.status_code == 409
        assert "Email already registered" in res.json()["detail"]

    async def test_register_duplicate_username(self, client: AsyncClient, test_user):
        res = await client.post(
            "/v1/auth/register",
            json={"email": "other@example.com", "username": "testuser", "password": "password123"},
        )
        assert res.status_code == 409
        assert "Username already taken" in res.json()["detail"]

    async def test_register_email_normalized_lowercase(self, client: AsyncClient):
        res = await client.post(
            "/v1/auth/register",
            json={"email": "USER@Example.COM", "username": "newuser", "password": "password123"},
        )
        assert res.status_code == 201

    async def test_register_invalid_email(self, client: AsyncClient):
        res = await client.post(
            "/v1/auth/register",
            json={"email": "not-an-email", "username": "newuser", "password": "password123"},
        )
        assert res.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        res = await client.post(
            "/v1/auth/register",
            json={"email": "new@example.com", "username": "newuser", "password": "short"},
        )
        assert res.status_code == 422

    async def test_register_invalid_username(self, client: AsyncClient):
        res = await client.post(
            "/v1/auth/register",
            json={"email": "new@example.com", "username": "a b", "password": "password123"},
        )
        assert res.status_code == 422

    async def test_register_username_too_short(self, client: AsyncClient):
        res = await client.post(
            "/v1/auth/register",
            json={"email": "new@example.com", "username": "ab", "password": "password123"},
        )
        assert res.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_user):
        res = await client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        res = await client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert res.status_code == 401
        assert "Invalid credentials" in res.json()["detail"]

    async def test_login_nonexistent_email(self, client: AsyncClient):
        res = await client.post(
            "/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert res.status_code == 401

    async def test_login_case_insensitive_email(self, client: AsyncClient, test_user):
        res = await client.post(
            "/v1/auth/login",
            json={"email": "TEST@example.com", "password": "password123"},
        )
        assert res.status_code == 200

    async def test_login_disabled_account(self, client: AsyncClient, db, test_user):
        test_user.is_active = False
        await db.commit()
        res = await client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert res.status_code == 401
        assert "Account disabled" in res.json()["detail"]


class TestRefresh:
    async def test_refresh_success(self, client: AsyncClient, test_user):
        # Login first to get tokens
        login_res = await client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        refresh_token = login_res.json()["refresh_token"]

        res = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should be different (rotation)
        assert data["refresh_token"] != refresh_token

    async def test_refresh_revoked_token(self, client: AsyncClient, test_user):
        login_res = await client.post(
            "/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        refresh_token = login_res.json()["refresh_token"]

        # Use it once
        await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})

        # Use it again — should fail (revoked after first use)
        res = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert res.status_code == 401

    async def test_refresh_invalid_token(self, client: AsyncClient):
        res = await client.post("/v1/auth/refresh", json={"refresh_token": "garbage"})
        assert res.status_code == 401


class TestLogout:
    async def test_logout_success(self, client: AsyncClient, test_user, auth_headers):
        res = await client.post("/v1/auth/logout", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["message"] == "Logged out"

    async def test_logout_blacklists_token(self, client: AsyncClient, test_user, auth_headers):
        # Logout
        await client.post("/v1/auth/logout", headers=auth_headers)

        # Try to use the blacklisted token
        res = await client.get("/v1/users/me", headers=auth_headers)
        assert res.status_code == 401

    async def test_logout_no_token(self, client: AsyncClient):
        res = await client.post("/v1/auth/logout")
        assert res.status_code == 403  # HTTPBearer returns 403 when missing


# ---------------------------------------------------------------------------
# Google-only user attempting password login
# ---------------------------------------------------------------------------
class TestGoogleOnlyUserLogin:
    async def test_google_only_user_password_login_rejected(self, client: AsyncClient, db: AsyncSession):
        """A user created via Google (no password_hash) gets a clear error on password login."""
        from app.core.security import hash_password  # noqa: F811

        google_user = User(
            email="googleonly@example.com",
            username="googleonly",
            password_hash=None,
            auth_provider="google",
            google_sub="google-sub-123",
        )
        db.add(google_user)
        await db.commit()

        res = await client.post(
            "/v1/auth/login",
            json={"email": "googleonly@example.com", "password": "anything"},
        )
        assert res.status_code == 400
        assert "Google sign-in" in res.json()["detail"]


# ---------------------------------------------------------------------------
# build_google_auth_url
# ---------------------------------------------------------------------------
class TestGoogleAuthUrl:
    async def test_returns_google_url(self, client: AsyncClient):
        res = await client.get("/v1/auth/google")
        assert res.status_code == 200
        url = res.json()["url"]
        assert url.startswith("https://accounts.google.com/o/oauth2/auth?")
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "scope=openid" in url
        assert "state=" in url

    async def test_url_contains_required_params(self, client: AsyncClient):
        res = await client.get("/v1/auth/google")
        url = res.json()["url"]
        assert "response_type=code" in url
        assert "access_type=offline" in url
        assert "prompt=select_account" in url


# ---------------------------------------------------------------------------
# Helpers for mocking Google OAuth
# ---------------------------------------------------------------------------
def _mock_google_token_exchange(*, status_code=200, json_data=None):
    """Return a mock httpx response for the Google token exchange POST."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = "mock error"
    return resp


def _mock_google_certs_response():
    """Return a mock httpx response for the Google certs GET."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"keys": []}
    return resp


def _make_async_client_mock(post_response, get_response):
    """Build an AsyncMock that behaves like httpx.AsyncClient as a context manager."""
    mock_client = AsyncMock()
    mock_client.post.return_value = post_response
    mock_client.get.return_value = get_response

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# Google OAuth callback (POST /v1/auth/google/callback)
# ---------------------------------------------------------------------------
class TestGoogleAuthCallback:
    """Tests for the full Google OAuth flow via the /v1/auth/google/callback endpoint."""

    async def test_new_user_creation(self, client: AsyncClient):
        """Successful Google auth creates a new user when none exists."""
        token_resp = _mock_google_token_exchange(
            json_data={"id_token": "fake.id.token", "access_token": "at"}
        )
        certs_resp = _mock_google_certs_response()
        claims = {"sub": "google-999", "email": "new.google@example.com", "name": "Jane Smith"}

        mock_client = _make_async_client_mock(token_resp, certs_resp)

        with (
            patch("app.services.auth_service.httpx.AsyncClient", return_value=mock_client),
            patch("app.services.auth_service.jose_jwt.decode", return_value=claims),
        ):
            res = await client.post("/v1/auth/google/callback", json={"code": "auth-code"})

        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_link_existing_user_by_email(self, client: AsyncClient, db: AsyncSession):
        """If a user with the same email exists, Google sub is linked to that user."""
        from app.core.security import hash_password

        existing = User(
            email="existing@example.com",
            username="existinguser",
            password_hash=hash_password("password123"),
        )
        db.add(existing)
        await db.commit()

        token_resp = _mock_google_token_exchange(
            json_data={"id_token": "fake.id.token", "access_token": "at"}
        )
        certs_resp = _mock_google_certs_response()
        claims = {"sub": "google-link-123", "email": "existing@example.com", "name": "Existing User"}

        mock_client = _make_async_client_mock(token_resp, certs_resp)

        with (
            patch("app.services.auth_service.httpx.AsyncClient", return_value=mock_client),
            patch("app.services.auth_service.jose_jwt.decode", return_value=claims),
        ):
            res = await client.post("/v1/auth/google/callback", json={"code": "auth-code"})

        assert res.status_code == 200
        assert "access_token" in res.json()

    async def test_token_exchange_failure(self, client: AsyncClient):
        """Non-200 from Google token endpoint returns 400."""
        token_resp = _mock_google_token_exchange(status_code=403, json_data={})
        certs_resp = _mock_google_certs_response()

        mock_client = _make_async_client_mock(token_resp, certs_resp)

        with patch("app.services.auth_service.httpx.AsyncClient", return_value=mock_client):
            res = await client.post("/v1/auth/google/callback", json={"code": "bad-code"})

        assert res.status_code == 400
        assert "Failed to authenticate with Google" in res.json()["detail"]

    async def test_missing_id_token(self, client: AsyncClient):
        """Google returns tokens but no id_token."""
        token_resp = _mock_google_token_exchange(
            json_data={"access_token": "at"}  # no id_token
        )
        certs_resp = _mock_google_certs_response()

        mock_client = _make_async_client_mock(token_resp, certs_resp)

        with patch("app.services.auth_service.httpx.AsyncClient", return_value=mock_client):
            res = await client.post("/v1/auth/google/callback", json={"code": "auth-code"})

        assert res.status_code == 400
        assert "No ID token" in res.json()["detail"]

    async def test_invalid_id_token(self, client: AsyncClient):
        """jose_jwt.decode raises an exception → 400."""
        token_resp = _mock_google_token_exchange(
            json_data={"id_token": "bad.jwt.token", "access_token": "at"}
        )
        certs_resp = _mock_google_certs_response()

        mock_client = _make_async_client_mock(token_resp, certs_resp)

        with (
            patch("app.services.auth_service.httpx.AsyncClient", return_value=mock_client),
            patch("app.services.auth_service.jose_jwt.decode", side_effect=Exception("decode failed")),
        ):
            res = await client.post("/v1/auth/google/callback", json={"code": "auth-code"})

        assert res.status_code == 400
        assert "Invalid Google ID token" in res.json()["detail"]

    async def test_no_email_in_claims(self, client: AsyncClient):
        """Google claims have no email → 400."""
        token_resp = _mock_google_token_exchange(
            json_data={"id_token": "fake.id.token", "access_token": "at"}
        )
        certs_resp = _mock_google_certs_response()
        claims = {"sub": "google-no-email", "name": "No Email"}

        mock_client = _make_async_client_mock(token_resp, certs_resp)

        with (
            patch("app.services.auth_service.httpx.AsyncClient", return_value=mock_client),
            patch("app.services.auth_service.jose_jwt.decode", return_value=claims),
        ):
            res = await client.post("/v1/auth/google/callback", json={"code": "auth-code"})

        assert res.status_code == 400
        assert "no email" in res.json()["detail"].lower()

    async def test_inactive_user_rejected(self, client: AsyncClient, db: AsyncSession):
        """Inactive user found by google_sub gets 401."""
        inactive = User(
            email="inactive.google@example.com",
            username="inactiveg",
            password_hash=None,
            auth_provider="google",
            google_sub="google-inactive-sub",
            is_active=False,
        )
        db.add(inactive)
        await db.commit()

        token_resp = _mock_google_token_exchange(
            json_data={"id_token": "fake.id.token", "access_token": "at"}
        )
        certs_resp = _mock_google_certs_response()
        claims = {"sub": "google-inactive-sub", "email": "inactive.google@example.com", "name": "Inactive"}

        mock_client = _make_async_client_mock(token_resp, certs_resp)

        with (
            patch("app.services.auth_service.httpx.AsyncClient", return_value=mock_client),
            patch("app.services.auth_service.jose_jwt.decode", return_value=claims),
        ):
            res = await client.post("/v1/auth/google/callback", json={"code": "auth-code"})

        assert res.status_code == 401
        assert "Account disabled" in res.json()["detail"]

    async def test_username_collision_increments(self, client: AsyncClient, db: AsyncSession):
        """When derived username already exists, a counter suffix is appended."""
        # Pre-create a user whose username matches what Google would derive
        blocker = User(
            email="blocker@example.com",
            username="jane_smith",
            password_hash=None,
            auth_provider="local",
        )
        db.add(blocker)
        await db.commit()

        token_resp = _mock_google_token_exchange(
            json_data={"id_token": "fake.id.token", "access_token": "at"}
        )
        certs_resp = _mock_google_certs_response()
        claims = {"sub": "google-collision", "email": "janesmith@example.com", "name": "Jane Smith"}

        mock_client = _make_async_client_mock(token_resp, certs_resp)

        with (
            patch("app.services.auth_service.httpx.AsyncClient", return_value=mock_client),
            patch("app.services.auth_service.jose_jwt.decode", return_value=claims),
        ):
            res = await client.post("/v1/auth/google/callback", json={"code": "auth-code"})

        assert res.status_code == 200
        # The new user should have been created (tokens returned)
        assert "access_token" in res.json()


# ---------------------------------------------------------------------------
# _derive_username static method
# ---------------------------------------------------------------------------
class TestDeriveUsername:
    def test_name_based(self):
        """'John Doe' becomes 'john_doe'."""
        assert AuthService._derive_username("j@example.com", "John Doe") == "john_doe"

    def test_short_name_falls_back_to_email(self):
        """Name shorter than 3 chars after sanitisation falls back to email local part."""
        result = AuthService._derive_username("hello@example.com", "AB")
        # "AB" → "ab" (len 2 < 3), so falls back to email local "hello"
        assert result == "hello"

    def test_email_fallback_normalisation(self):
        """Special chars in email local part are replaced and normalised."""
        result = AuthService._derive_username("my.cool+tag@example.com", "")
        # "my.cool+tag" → "my_cool_tag"
        assert result == "my_cool_tag"

    def test_short_email_local_appends_user(self):
        """Email local part shorter than 3 chars gets '_user' appended."""
        result = AuthService._derive_username("ab@example.com", "")
        assert result == "ab_user"

    def test_very_short_email_local(self):
        """Single char email local part gets '_user' suffix."""
        result = AuthService._derive_username("x@example.com", "")
        assert result == "x_user"
