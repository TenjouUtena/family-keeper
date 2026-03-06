import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    hash_password,
)
from app.models import User

pytestmark = pytest.mark.anyio


# --- Helpers ---


async def create_family_with_member(
    client: AsyncClient, auth_headers: dict
) -> str:
    """Create a family and return its ID."""
    resp = await client.post(
        "/v1/families", json={"name": "Test Family"}, headers=auth_headers
    )
    return resp.json()["id"]


async def create_second_user(
    db: AsyncSession,
) -> tuple[User, dict[str, str]]:
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


async def join_family(
    client: AsyncClient,
    family_id: str,
    admin_headers: dict,
    joiner_headers: dict,
) -> None:
    """Have joiner join the family via invite code."""
    inv = await client.post(
        f"/v1/families/{family_id}/invites", headers=admin_headers
    )
    code = inv.json()["code"]
    await client.post(
        "/v1/families/join", json={"code": code}, headers=joiner_headers
    )


# --- Create List ---


async def test_create_list(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Groceries", "list_type": "grocery"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Groceries"
    assert data["list_type"] == "grocery"
    assert data["item_count"] == 0
    assert data["require_photo_completion"] is False


async def test_create_chore_list_as_child_forbidden(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
):
    fid = await create_family_with_member(client, auth_headers)
    _, child_headers = await create_second_user(db)
    await join_family(client, fid, auth_headers, child_headers)

    resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Chores", "list_type": "chores"},
        headers=child_headers,
    )
    assert resp.status_code == 403
    assert "parent" in resp.json()["detail"].lower()


# --- Get Lists ---


async def test_get_lists(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)
    await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Groceries", "list_type": "grocery"},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/v1/families/{fid}/lists", headers=auth_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# --- Get List Detail ---


async def test_get_list_detail(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Shopping"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    resp = await client.get(
        f"/v1/families/{fid}/lists/{lid}", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Shopping"
    assert data["items"] == []


# --- Update List ---


async def test_update_list(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Old Name"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    resp = await client.patch(
        f"/v1/families/{fid}/lists/{lid}",
        json={"name": "New Name", "require_photo_completion": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["require_photo_completion"] is True


# --- Add Items ---


async def test_add_single_item(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}/items",
        json={"items": [{"content": "Buy milk"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 1
    assert data[0]["content"] == "Buy milk"
    assert data[0]["status"] == "pending"


async def test_bulk_add_items(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Groceries"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}/items",
        json={
            "items": [
                {"content": "Milk"},
                {"content": "Eggs"},
                {"content": "Bread"},
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 3
    # Check positions are gapped
    positions = [item["position"] for item in data]
    assert positions[0] < positions[1] < positions[2]


# --- Update Item ---


async def test_update_item_status(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    items_resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}/items",
        json={"items": [{"content": "Task 1"}]},
        headers=auth_headers,
    )
    item_id = items_resp.json()[0]["id"]

    resp = await client.patch(
        f"/v1/families/{fid}/lists/{lid}/items/{item_id}",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert data["completed_at"] is not None
    assert data["completed_by"] is not None


async def test_update_item_undo_done(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    items_resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}/items",
        json={"items": [{"content": "Task 1"}]},
        headers=auth_headers,
    )
    item_id = items_resp.json()[0]["id"]

    # Mark done
    await client.patch(
        f"/v1/families/{fid}/lists/{lid}/items/{item_id}",
        json={"status": "done"},
        headers=auth_headers,
    )

    # Undo
    resp = await client.patch(
        f"/v1/families/{fid}/lists/{lid}/items/{item_id}",
        json={"status": "pending"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    assert resp.json()["completed_at"] is None


# --- Photo Completion Enforcement ---


async def test_photo_required_blocks_done(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={
            "name": "Chores",
            "list_type": "chores",
            "require_photo_completion": True,
        },
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    items_resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}/items",
        json={"items": [{"content": "Clean room"}]},
        headers=auth_headers,
    )
    item_id = items_resp.json()[0]["id"]

    resp = await client.patch(
        f"/v1/families/{fid}/lists/{lid}/items/{item_id}",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "photo" in resp.json()["detail"].lower()


# --- Delete Item ---


async def test_delete_item(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    items_resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}/items",
        json={"items": [{"content": "Delete me"}]},
        headers=auth_headers,
    )
    item_id = items_resp.json()[0]["id"]

    resp = await client.delete(
        f"/v1/families/{fid}/lists/{lid}/items/{item_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Verify deleted
    detail = await client.get(
        f"/v1/families/{fid}/lists/{lid}", headers=auth_headers
    )
    assert len(detail.json()["items"]) == 0


# --- Reorder Items ---


async def test_reorder_items(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    items_resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}/items",
        json={
            "items": [
                {"content": "First"},
                {"content": "Second"},
                {"content": "Third"},
            ]
        },
        headers=auth_headers,
    )
    items = items_resp.json()

    # Reverse the order
    resp = await client.patch(
        f"/v1/families/{fid}/lists/{lid}/items/reorder",
        json={
            "items": [
                {"id": items[2]["id"], "position": 100},
                {"id": items[1]["id"], "position": 200},
                {"id": items[0]["id"], "position": 300},
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["content"] == "Third"
    assert data[1]["content"] == "Second"
    assert data[2]["content"] == "First"


# --- Completion tracking ---


async def test_completion_records_username(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)
    lst = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = lst.json()["id"]

    items = await client.post(
        f"/v1/families/{fid}/lists/{lid}/items",
        json={"items": [{"content": "Task"}]},
        headers=auth_headers,
    )
    iid = items.json()[0]["id"]

    resp = await client.patch(
        f"/v1/families/{fid}/lists/{lid}/items/{iid}",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed_by_username"] is not None
    assert data["completed_at"] is not None


async def test_child_cannot_undo_done(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
):
    """A child member cannot undo a completed item."""
    fid = await create_family_with_member(client, auth_headers)
    _, child_headers = await create_second_user(db)
    await join_family(client, fid, auth_headers, child_headers)

    # Parent creates list and item
    lst = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Chores", "list_type": "chores"},
        headers=auth_headers,
    )
    lid = lst.json()["id"]

    items = await client.post(
        f"/v1/families/{fid}/lists/{lid}/items",
        json={"items": [{"content": "Clean room"}]},
        headers=auth_headers,
    )
    iid = items.json()[0]["id"]

    # Child marks it done
    resp = await client.patch(
        f"/v1/families/{fid}/lists/{lid}/items/{iid}",
        json={"status": "done"},
        headers=child_headers,
    )
    assert resp.status_code == 200

    # Child tries to undo — should fail
    resp = await client.patch(
        f"/v1/families/{fid}/lists/{lid}/items/{iid}",
        json={"status": "pending"},
        headers=child_headers,
    )
    assert resp.status_code == 403
    assert "parent" in resp.json()["detail"].lower()

    # Parent can undo
    resp = await client.patch(
        f"/v1/families/{fid}/lists/{lid}/items/{iid}",
        json={"status": "pending"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


# --- Non-member access ---


async def test_non_member_cannot_access_lists(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
):
    fid = await create_family_with_member(client, auth_headers)
    _, other_headers = await create_second_user(db)

    resp = await client.get(
        f"/v1/families/{fid}/lists", headers=other_headers
    )
    assert resp.status_code == 403


# --- Attachment URL ---


async def test_get_attachment_url_not_found(
    client: AsyncClient,
    auth_headers: dict,
):
    """GET attachment URL returns 404 for non-existent attachment."""
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    items_resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}/items",
        json={"items": [{"content": "Task"}]},
        headers=auth_headers,
    )
    item_id = items_resp.json()[0]["id"]

    fake_attachment_id = str(uuid.uuid4())
    resp = await client.get(
        f"/v1/families/{fid}/lists/{lid}/items/{item_id}"
        f"/attachments/{fake_attachment_id}/url",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert "attachment" in resp.json()["detail"].lower()


# --- SSE Stream Auth ---


async def test_stream_invalid_token(
    client: AsyncClient,
    auth_headers: dict,
):
    """SSE stream rejects a completely invalid JWT."""
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    resp = await client.get(
        f"/v1/families/{fid}/lists/{lid}/stream",
        params={"token": "not-a-valid-jwt"},
    )
    assert resp.status_code == 401
    assert "invalid token" in resp.json()["detail"].lower()


async def test_stream_refresh_token_rejected(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
):
    """SSE stream rejects a refresh token (wrong type)."""
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    refresh_token, _ = create_refresh_token(test_user.id)
    resp = await client.get(
        f"/v1/families/{fid}/lists/{lid}/stream",
        params={"token": refresh_token},
    )
    assert resp.status_code == 401
    assert "token type" in resp.json()["detail"].lower()


async def test_stream_blacklisted_token(
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
):
    """SSE stream rejects a blacklisted access token."""
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    access_token, jti = create_access_token(test_user.id)
    await blacklist_token(jti, ttl_seconds=300)

    resp = await client.get(
        f"/v1/families/{fid}/lists/{lid}/stream",
        params={"token": access_token},
    )
    assert resp.status_code == 401
    assert "revoked" in resp.json()["detail"].lower()


async def test_stream_non_member_forbidden(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
):
    """SSE stream returns 403 for a valid user who is not a family member."""
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    # Create a second user who is NOT a member of this family
    _, other_headers = await create_second_user(db)
    # Extract raw token from the other user's headers
    other_token = other_headers["Authorization"].removeprefix("Bearer ")

    resp = await client.get(
        f"/v1/families/{fid}/lists/{lid}/stream",
        params={"token": other_token},
    )
    assert resp.status_code == 403
    assert "not a member" in resp.json()["detail"].lower()


@patch("app.routers.lists.subscribe_list")
async def test_stream_valid_returns_event_stream(
    mock_subscribe: AsyncMock,
    client: AsyncClient,
    auth_headers: dict,
    test_user: User,
):
    """SSE stream returns 200 with text/event-stream for a valid member."""
    fid = await create_family_with_member(client, auth_headers)
    create_resp = await client.post(
        f"/v1/families/{fid}/lists",
        json={"name": "Todo"},
        headers=auth_headers,
    )
    lid = create_resp.json()["id"]

    # Mock subscribe_list to return a fake pubsub that raises on first
    # get_message call, causing the generator to exit (and the response to end).
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(
        side_effect=ConnectionError("test: break stream loop")
    )
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.aclose = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mock_subscribe.return_value = (mock_pubsub, mock_redis)

    access_token, _ = create_access_token(test_user.id)
    resp = await client.get(
        f"/v1/families/{fid}/lists/{lid}/stream",
        params={"token": access_token},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
