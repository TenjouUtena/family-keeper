from httpx import AsyncClient

from app.models import User


class TestGetMe:
    async def test_get_me_success(self, client: AsyncClient, test_user, auth_headers):
        res = await client.get("/v1/users/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "password_hash" not in data

    async def test_get_me_no_auth(self, client: AsyncClient):
        res = await client.get("/v1/users/me")
        assert res.status_code == 403

    async def test_get_me_invalid_token(self, client: AsyncClient):
        res = await client.get("/v1/users/me", headers={"Authorization": "Bearer invalid"})
        assert res.status_code == 401


class TestUpdateMe:
    async def test_update_username(self, client: AsyncClient, test_user, auth_headers):
        res = await client.patch(
            "/v1/users/me", headers=auth_headers, json={"username": "newname"}
        )
        assert res.status_code == 200
        assert res.json()["username"] == "newname"

    async def test_update_avatar_url(self, client: AsyncClient, test_user, auth_headers):
        res = await client.patch(
            "/v1/users/me",
            headers=auth_headers,
            json={"avatar_url": "https://example.com/avatar.png"},
        )
        assert res.status_code == 200
        assert res.json()["avatar_url"] == "https://example.com/avatar.png"

    async def test_update_username_conflict(self, client: AsyncClient, db, test_user, auth_headers):
        from app.core.security import hash_password

        other = User(
            email="other@example.com",
            username="taken",
            password_hash=hash_password("password123"),
        )
        db.add(other)
        await db.commit()

        res = await client.patch(
            "/v1/users/me", headers=auth_headers, json={"username": "taken"}
        )
        assert res.status_code == 409
        assert "Username already taken" in res.json()["detail"]

    async def test_update_invalid_username(self, client: AsyncClient, test_user, auth_headers):
        res = await client.patch(
            "/v1/users/me", headers=auth_headers, json={"username": "a b"}
        )
        assert res.status_code == 422

    async def test_update_no_auth(self, client: AsyncClient):
        res = await client.patch("/v1/users/me", json={"username": "newname"})
        assert res.status_code == 403

    async def test_update_empty_body(self, client: AsyncClient, test_user, auth_headers):
        res = await client.patch("/v1/users/me", headers=auth_headers, json={})
        assert res.status_code == 200
        # No changes, returns same data
        assert res.json()["username"] == "testuser"
