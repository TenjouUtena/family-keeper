from httpx import AsyncClient


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
