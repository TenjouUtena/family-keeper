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
        "/v1/families", json={"name": "AI Test Family"}, headers=auth_headers
    )
    return resp.json()["id"]


def _make_mock_anthropic(response_text: str = '[{"content": "Milk"}, {"content": "Eggs"}]'):
    """Create a mock AsyncAnthropic client."""
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=response_text)]
    mock_message.usage.input_tokens = 1000
    mock_message.usage.output_tokens = 50
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)
    return mock_client


# Minimal valid JPEG bytes (just enough header to pass content_type check)
FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100


# --- Tests ---


@patch("app.services.ai_service.anthropic.AsyncAnthropic")
async def test_image_to_list_success(
    mock_cls, client: AsyncClient, auth_headers: dict
):
    mock_cls.return_value = _make_mock_anthropic()
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.post(
        f"/v1/families/{fid}/ai/image-to-list",
        headers=auth_headers,
        files={"image": ("test.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["items"][0]["content"] == "Milk"
    assert data["items"][1]["content"] == "Eggs"
    assert data["input_tokens"] == 1000
    assert data["output_tokens"] == 50


@patch("app.services.ai_service.anthropic.AsyncAnthropic")
async def test_image_to_list_with_markdown_fences(
    mock_cls, client: AsyncClient, auth_headers: dict
):
    mock_cls.return_value = _make_mock_anthropic(
        '```json\n[{"content": "Bread"}]\n```'
    )
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.post(
        f"/v1/families/{fid}/ai/image-to-list",
        headers=auth_headers,
        files={"image": ("test.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 200
    assert resp.json()["items"][0]["content"] == "Bread"


@patch("app.services.ai_service.anthropic.AsyncAnthropic")
async def test_image_to_list_with_list_type(
    mock_cls, client: AsyncClient, auth_headers: dict
):
    mock_cls.return_value = _make_mock_anthropic()
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.post(
        f"/v1/families/{fid}/ai/image-to-list",
        headers=auth_headers,
        files={"image": ("test.jpg", FAKE_JPEG, "image/jpeg")},
        data={"list_type": "grocery"},
    )
    assert resp.status_code == 200


async def test_image_to_list_unsupported_type(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.post(
        f"/v1/families/{fid}/ai/image-to-list",
        headers=auth_headers,
        files={"image": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
    assert "Unsupported image type" in resp.json()["detail"]


async def test_image_to_list_too_large(
    client: AsyncClient, auth_headers: dict
):
    fid = await create_family_with_member(client, auth_headers)

    big_image = b"\xff\xd8\xff\xe0" + b"\x00" * (11 * 1024 * 1024)
    resp = await client.post(
        f"/v1/families/{fid}/ai/image-to-list",
        headers=auth_headers,
        files={"image": ("big.jpg", big_image, "image/jpeg")},
    )
    assert resp.status_code == 400
    assert "too large" in resp.json()["detail"]


@patch("app.services.ai_service.anthropic.AsyncAnthropic")
async def test_image_to_list_malformed_response(
    mock_cls, client: AsyncClient, auth_headers: dict
):
    mock_cls.return_value = _make_mock_anthropic("This is not JSON at all")
    fid = await create_family_with_member(client, auth_headers)

    resp = await client.post(
        f"/v1/families/{fid}/ai/image-to-list",
        headers=auth_headers,
        files={"image": ("test.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 422
    assert "Could not extract" in resp.json()["detail"]


@patch("app.services.ai_service.anthropic.AsyncAnthropic")
async def test_image_to_list_rate_limit(
    mock_cls, client: AsyncClient, auth_headers: dict
):
    mock_cls.return_value = _make_mock_anthropic()
    fid = await create_family_with_member(client, auth_headers)

    # Send 11 requests (limit is 10)
    for i in range(11):
        resp = await client.post(
            f"/v1/families/{fid}/ai/image-to-list",
            headers=auth_headers,
            files={"image": ("test.jpg", FAKE_JPEG, "image/jpeg")},
        )
        if i < 10:
            assert resp.status_code == 200
        else:
            assert resp.status_code == 429
            assert "rate limit" in resp.json()["detail"].lower()


async def test_image_to_list_unauthenticated(client: AsyncClient):
    resp = await client.post(
        "/v1/families/00000000-0000-0000-0000-000000000000/ai/image-to-list",
        files={"image": ("test.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code in (401, 403)


async def test_image_to_list_non_member(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    # Create family with first user
    fid = await create_family_with_member(client, auth_headers)

    # Create second user who is NOT a member
    user2 = User(
        email="other@example.com",
        username="otheruser",
        password_hash=hash_password("password123"),
    )
    db.add(user2)
    await db.commit()
    await db.refresh(user2)
    token2, _ = create_access_token(user2.id)
    headers2 = {"Authorization": f"Bearer {token2}"}

    resp = await client.post(
        f"/v1/families/{fid}/ai/image-to-list",
        headers=headers2,
        files={"image": ("test.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 403
