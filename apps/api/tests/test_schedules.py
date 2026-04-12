import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models import User

pytestmark = pytest.mark.anyio


# --- Helpers ---


async def create_family_with_member(client: AsyncClient, auth_headers: dict) -> str:
    resp = await client.post(
        "/v1/families", json={"name": "Schedule Test Family"}, headers=auth_headers
    )
    return resp.json()["id"]


async def create_second_user(db: AsyncSession) -> tuple[User, dict[str, str]]:
    user = User(
        email="sched_second@example.com",
        username="scheduser2",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token, _ = create_access_token(user.id)
    return user, {"Authorization": f"Bearer {token}"}


async def join_family(
    client: AsyncClient, family_id: str, admin_headers: dict, joiner_headers: dict
) -> None:
    inv = await client.post(f"/v1/families/{family_id}/invites", headers=admin_headers)
    code = inv.json()["code"]
    await client.post("/v1/families/join", json={"code": code}, headers=joiner_headers)


async def create_schedule(client: AsyncClient, family_id: str, auth_headers: dict) -> str:
    resp = await client.post(
        f"/v1/families/{family_id}/schedules",
        json={"name": "Test Schedule"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# --- Schedule CRUD ---


async def test_create_schedule(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.post(
        f"/v1/families/{fid}/schedules",
        json={"name": "Soccer Season", "description": "Spring 2026"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Soccer Season"
    assert data["description"] == "Spring 2026"
    assert data["event_count"] == 0
    assert data["is_archived"] is False


async def test_get_schedules(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)
    await create_schedule(client, fid, auth_headers)
    await create_schedule(client, fid, auth_headers)

    resp = await client.get(f"/v1/families/{fid}/schedules", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_get_schedule_detail(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)
    sid = await create_schedule(client, fid, auth_headers)

    resp = await client.get(
        f"/v1/families/{fid}/schedules/{sid}", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Schedule"
    assert data["events"] == []


async def test_update_schedule(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)
    sid = await create_schedule(client, fid, auth_headers)

    resp = await client.patch(
        f"/v1/families/{fid}/schedules/{sid}",
        json={"name": "Updated Schedule", "description": "New desc"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Schedule"


async def test_archive_schedule(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)
    sid = await create_schedule(client, fid, auth_headers)

    await client.patch(
        f"/v1/families/{fid}/schedules/{sid}",
        json={"is_archived": True},
        headers=auth_headers,
    )

    # Archived schedules should not appear in list
    resp = await client.get(f"/v1/families/{fid}/schedules", headers=auth_headers)
    assert len(resp.json()) == 0


# --- Event CRUD ---


async def test_add_events(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)
    sid = await create_schedule(client, fid, auth_headers)

    resp = await client.post(
        f"/v1/families/{fid}/schedules/{sid}/events",
        json={
            "events": [
                {"title": "Practice", "start_at": "2026-04-15T16:00:00Z"},
                {"title": "Game Day", "start_at": "2026-04-20T10:00:00Z", "all_day": False},
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2
    assert data[0]["title"] == "Practice"
    assert data[1]["title"] == "Game Day"


async def test_events_ordered_by_date(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)
    sid = await create_schedule(client, fid, auth_headers)

    # Add events out of order
    await client.post(
        f"/v1/families/{fid}/schedules/{sid}/events",
        json={
            "events": [
                {"title": "Later", "start_at": "2026-05-01T10:00:00Z"},
                {"title": "Earlier", "start_at": "2026-04-01T10:00:00Z"},
            ]
        },
        headers=auth_headers,
    )

    resp = await client.get(
        f"/v1/families/{fid}/schedules/{sid}", headers=auth_headers
    )
    events = resp.json()["events"]
    assert events[0]["title"] == "Earlier"
    assert events[1]["title"] == "Later"


async def test_update_event(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)
    sid = await create_schedule(client, fid, auth_headers)

    add_resp = await client.post(
        f"/v1/families/{fid}/schedules/{sid}/events",
        json={"events": [{"title": "Original", "start_at": "2026-04-15T16:00:00Z"}]},
        headers=auth_headers,
    )
    event_id = add_resp.json()[0]["id"]

    resp = await client.patch(
        f"/v1/families/{fid}/schedules/{sid}/events/{event_id}",
        json={"title": "Updated", "location": "City Park"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"
    assert resp.json()["location"] == "City Park"


async def test_complete_event(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)
    sid = await create_schedule(client, fid, auth_headers)

    add_resp = await client.post(
        f"/v1/families/{fid}/schedules/{sid}/events",
        json={"events": [{"title": "Task", "start_at": "2026-04-15T10:00:00Z"}]},
        headers=auth_headers,
    )
    event_id = add_resp.json()[0]["id"]

    resp = await client.patch(
        f"/v1/families/{fid}/schedules/{sid}/events/{event_id}",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert data["completed_at"] is not None
    assert data["completed_by"] is not None


async def test_delete_event(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)
    sid = await create_schedule(client, fid, auth_headers)

    add_resp = await client.post(
        f"/v1/families/{fid}/schedules/{sid}/events",
        json={"events": [{"title": "To Delete", "start_at": "2026-04-15T10:00:00Z"}]},
        headers=auth_headers,
    )
    event_id = add_resp.json()[0]["id"]

    resp = await client.delete(
        f"/v1/families/{fid}/schedules/{sid}/events/{event_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Event deleted"

    # Verify deleted
    detail = await client.get(
        f"/v1/families/{fid}/schedules/{sid}", headers=auth_headers
    )
    assert len(detail.json()["events"]) == 0


# --- Auth & Permission ---


async def test_schedule_requires_auth(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.get(f"/v1/families/{fid}/schedules")
    assert resp.status_code in (401, 403)


async def test_non_member_cannot_access_schedules(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    fid = await create_family_with_member(client, auth_headers)
    _, other_headers = await create_second_user(db)

    resp = await client.get(f"/v1/families/{fid}/schedules", headers=other_headers)
    assert resp.status_code == 403


async def test_child_cannot_undo_completed_event(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    fid = await create_family_with_member(client, auth_headers)
    sid = await create_schedule(client, fid, auth_headers)

    # Join child
    _, child_headers = await create_second_user(db)
    await join_family(client, fid, auth_headers, child_headers)

    # Add and complete an event
    add_resp = await client.post(
        f"/v1/families/{fid}/schedules/{sid}/events",
        json={"events": [{"title": "Homework", "start_at": "2026-04-15T10:00:00Z"}]},
        headers=auth_headers,
    )
    event_id = add_resp.json()[0]["id"]

    await client.patch(
        f"/v1/families/{fid}/schedules/{sid}/events/{event_id}",
        json={"status": "done"},
        headers=auth_headers,
    )

    # Child tries to undo
    resp = await client.patch(
        f"/v1/families/{fid}/schedules/{sid}/events/{event_id}",
        json={"status": "pending"},
        headers=child_headers,
    )
    assert resp.status_code == 403


async def test_role_visibility(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    fid = await create_family_with_member(client, auth_headers)

    # Create parent-only schedule
    resp = await client.post(
        f"/v1/families/{fid}/schedules",
        json={"name": "Parent Schedule", "visible_to_role": "parent"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # Join child
    _, child_headers = await create_second_user(db)
    await join_family(client, fid, auth_headers, child_headers)

    # Child should not see the schedule
    resp = await client.get(f"/v1/families/{fid}/schedules", headers=child_headers)
    assert len(resp.json()) == 0


# --- AI scan for schedules ---


FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100


def _make_mock_anthropic(
    response_text: str = '[{"title": "Soccer", "start_at": "2026-04-15T16:00:00", "end_at": null, "all_day": false, "location": "Park", "notes": null}]',
):
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=response_text)]
    mock_message.usage.input_tokens = 1200
    mock_message.usage.output_tokens = 80
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)
    return mock_client


@patch("app.services.ai_service.anthropic.AsyncAnthropic")
async def test_image_to_schedule_success(
    mock_cls, client: AsyncClient, auth_headers: dict
):
    mock_cls.return_value = _make_mock_anthropic()
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.post(
        f"/v1/families/{fid}/ai/image-to-schedule",
        headers=auth_headers,
        files={"image": ("test.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["title"] == "Soccer"
    assert data["events"][0]["location"] == "Park"
    assert data["input_tokens"] == 1200


@patch("app.services.ai_service.anthropic.AsyncAnthropic")
async def test_image_to_schedule_bad_json(
    mock_cls, client: AsyncClient, auth_headers: dict
):
    mock_cls.return_value = _make_mock_anthropic(response_text="not valid json")
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.post(
        f"/v1/families/{fid}/ai/image-to-schedule",
        headers=auth_headers,
        files={"image": ("test.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 422


async def test_image_to_schedule_unsupported_type(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.post(
        f"/v1/families/{fid}/ai/image-to-schedule",
        headers=auth_headers,
        files={"image": ("test.gif", b"GIF89a", "image/gif")},
    )
    assert resp.status_code == 400


async def test_schedule_not_found(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)
    fake_id = str(uuid.uuid4())

    resp = await client.get(
        f"/v1/families/{fid}/schedules/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


async def test_event_not_found(client: AsyncClient, auth_headers: dict):
    fid = await create_family_with_member(client, auth_headers)
    sid = await create_schedule(client, fid, auth_headers)
    fake_id = str(uuid.uuid4())

    resp = await client.patch(
        f"/v1/families/{fid}/schedules/{sid}/events/{fake_id}",
        json={"title": "nope"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
