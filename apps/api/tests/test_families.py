import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models import User

pytestmark = pytest.mark.anyio


# --- Helpers ---


async def create_second_user(db: AsyncSession) -> tuple[User, dict[str, str]]:
    user = User(
        email="second@example.com",
        username="seconduser",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token, _ = create_access_token(user.id)
    return user, {"Authorization": f"Bearer {token}"}


# --- Create Family ---


async def test_create_family(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/v1/families", json={"name": "Smith Family"}, headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Smith Family"
    assert data["parent_role_name"] == "Parent"
    assert data["child_role_name"] == "Child"
    assert data["member_count"] == 1


async def test_create_family_unauthenticated(client: AsyncClient):
    resp = await client.post("/v1/families", json={"name": "Family"})
    assert resp.status_code == 403


async def test_create_family_empty_name(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/v1/families", json={"name": ""}, headers=auth_headers)
    assert resp.status_code == 422


# --- List Families ---


async def test_list_families(client: AsyncClient, auth_headers: dict):
    await client.post("/v1/families", json={"name": "Family A"}, headers=auth_headers)
    await client.post("/v1/families", json={"name": "Family B"}, headers=auth_headers)

    resp = await client.get("/v1/families", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


async def test_list_families_only_own(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await client.post("/v1/families", json={"name": "My Family"}, headers=auth_headers)
    _, other_headers = await create_second_user(db)
    await client.post("/v1/families", json={"name": "Other Family"}, headers=other_headers)

    resp = await client.get("/v1/families", headers=auth_headers)
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "My Family"


# --- Get Family ---


async def test_get_family(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/v1/families", json={"name": "Test Family"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    resp = await client.get(f"/v1/families/{family_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Family"
    assert len(data["members"]) == 1
    assert data["members"][0]["role"] == "parent"
    assert data["members"][0]["is_admin"] is True


async def test_get_family_non_member(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    create_resp = await client.post(
        "/v1/families", json={"name": "Private Family"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    _, other_headers = await create_second_user(db)
    resp = await client.get(f"/v1/families/{family_id}", headers=other_headers)
    assert resp.status_code == 403


# --- Update Family ---


async def test_update_family(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/v1/families", json={"name": "Old Name"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/v1/families/{family_id}",
        json={"name": "New Name", "parent_role_name": "Mom/Dad"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["parent_role_name"] == "Mom/Dad"


async def test_update_family_non_admin(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    create_resp = await client.post(
        "/v1/families", json={"name": "Family"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    # Second user joins as child (non-admin)
    invite_resp = await client.post(
        f"/v1/families/{family_id}/invites", headers=auth_headers
    )
    code = invite_resp.json()["code"]

    _, other_headers = await create_second_user(db)
    await client.post("/v1/families/join", json={"code": code}, headers=other_headers)

    resp = await client.patch(
        f"/v1/families/{family_id}",
        json={"name": "Hacked"},
        headers=other_headers,
    )
    assert resp.status_code == 403


# --- Invite Codes ---


async def test_create_invite(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/v1/families", json={"name": "Family"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    resp = await client.post(
        f"/v1/families/{family_id}/invites",
        json={"max_uses": 5, "expires_in_hours": 24},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["code"]) == 8
    assert data["max_uses"] == 5


async def test_create_invite_default_params(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/v1/families", json={"name": "Family"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    resp = await client.post(
        f"/v1/families/{family_id}/invites", headers=auth_headers
    )
    assert resp.status_code == 201
    assert resp.json()["max_uses"] == 10


# --- Join Family ---


async def test_join_family(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    create_resp = await client.post(
        "/v1/families", json={"name": "Welcome Family"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    invite_resp = await client.post(
        f"/v1/families/{family_id}/invites", headers=auth_headers
    )
    code = invite_resp.json()["code"]

    _, other_headers = await create_second_user(db)
    resp = await client.post(
        "/v1/families/join", json={"code": code}, headers=other_headers
    )
    assert resp.status_code == 200
    assert resp.json()["member_count"] == 2

    # Verify they can see the family
    detail_resp = await client.get(f"/v1/families/{family_id}", headers=other_headers)
    assert detail_resp.status_code == 200
    members = detail_resp.json()["members"]
    new_member = [m for m in members if m["username"] == "seconduser"][0]
    assert new_member["role"] == "child"
    assert new_member["is_admin"] is False


async def test_join_family_invalid_code(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/v1/families/join", json={"code": "BADCODE1"}, headers=auth_headers
    )
    assert resp.status_code == 404


async def test_join_family_already_member(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/v1/families", json={"name": "Family"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    invite_resp = await client.post(
        f"/v1/families/{family_id}/invites", headers=auth_headers
    )
    code = invite_resp.json()["code"]

    resp = await client.post(
        "/v1/families/join", json={"code": code}, headers=auth_headers
    )
    assert resp.status_code == 409


# --- Revoke Invite ---


async def test_revoke_invite(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    create_resp = await client.post(
        "/v1/families", json={"name": "Family"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    invite_resp = await client.post(
        f"/v1/families/{family_id}/invites", headers=auth_headers
    )
    code = invite_resp.json()["code"]

    # Revoke it
    resp = await client.delete(
        f"/v1/families/{family_id}/invites/{code}", headers=auth_headers
    )
    assert resp.status_code == 200

    # Try to join with revoked code
    _, other_headers = await create_second_user(db)
    join_resp = await client.post(
        "/v1/families/join", json={"code": code}, headers=other_headers
    )
    assert join_resp.status_code == 404


# --- Update Member Role ---


async def test_update_member_role(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    create_resp = await client.post(
        "/v1/families", json={"name": "Family"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    invite_resp = await client.post(
        f"/v1/families/{family_id}/invites", headers=auth_headers
    )
    code = invite_resp.json()["code"]

    second_user, other_headers = await create_second_user(db)
    await client.post("/v1/families/join", json={"code": code}, headers=other_headers)

    # Promote to parent + admin
    resp = await client.patch(
        f"/v1/families/{family_id}/members/{second_user.id}",
        json={"role": "parent", "is_admin": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "parent"
    assert resp.json()["is_admin"] is True


# --- Remove Member ---


async def test_remove_member(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    create_resp = await client.post(
        "/v1/families", json={"name": "Family"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    invite_resp = await client.post(
        f"/v1/families/{family_id}/invites", headers=auth_headers
    )
    code = invite_resp.json()["code"]

    second_user, other_headers = await create_second_user(db)
    await client.post("/v1/families/join", json={"code": code}, headers=other_headers)

    # Remove the second user
    resp = await client.delete(
        f"/v1/families/{family_id}/members/{second_user.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Verify removed
    detail_resp = await client.get(f"/v1/families/{family_id}", headers=auth_headers)
    assert len(detail_resp.json()["members"]) == 1


async def test_remove_last_admin(client: AsyncClient, auth_headers: dict, test_user: User):
    create_resp = await client.post(
        "/v1/families", json={"name": "Family"}, headers=auth_headers
    )
    family_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/v1/families/{family_id}/members/{test_user.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "last admin" in resp.json()["detail"]
