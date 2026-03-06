import io
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


# --- Compression / _compress_image tests ---


def _make_test_image(width: int, height: int, mode: str = "RGB") -> bytes:
    """Create a test image in memory and return its bytes."""
    from PIL import Image as PILImage

    color = (255, 0, 0, 128) if "A" in mode else (255, 0, 0)
    img = PILImage.new(mode, (width, height), color=color)
    buf = io.BytesIO()
    fmt = "PNG" if mode in ("RGBA", "P", "LA") else "JPEG"
    img.save(buf, format=fmt)
    return buf.getvalue()


async def test_compress_image_rgba_to_rgb():
    """RGBA PNG input is converted to RGB JPEG output."""
    from app.services.ai_service import AIService

    rgba_bytes = _make_test_image(100, 100, mode="RGBA")
    result_bytes, result_mime = AIService._compress_image(rgba_bytes, "image/png")

    assert result_mime == "image/jpeg"
    # JPEG files start with the SOI marker \xff\xd8
    assert result_bytes[:2] == b"\xff\xd8"


async def test_compress_image_downscales_large():
    """Images larger than MAX_IMAGE_DIMENSION (2048) are downscaled."""
    from PIL import Image as PILImage

    from app.services.ai_service import AIService, MAX_IMAGE_DIMENSION

    large_bytes = _make_test_image(4000, 3000)
    result_bytes, result_mime = AIService._compress_image(large_bytes, "image/jpeg")

    assert result_mime == "image/jpeg"
    # Verify the resulting image dimensions are within the limit
    result_img = PILImage.open(io.BytesIO(result_bytes))
    assert max(result_img.size) <= MAX_IMAGE_DIMENSION


async def test_compress_image_small_passthrough():
    """A small RGB JPEG is returned as JPEG without aggressive resize."""
    from PIL import Image as PILImage

    from app.services.ai_service import AIService

    small_bytes = _make_test_image(200, 150)
    result_bytes, result_mime = AIService._compress_image(small_bytes, "image/jpeg")

    assert result_mime == "image/jpeg"
    assert result_bytes[:2] == b"\xff\xd8"
    # Small image should not be aggressively halved; dimensions should remain reasonable
    result_img = PILImage.open(io.BytesIO(result_bytes))
    assert result_img.size[0] >= 100  # Should not be halved from 200


@patch("app.services.ai_service.anthropic.AsyncAnthropic")
@patch("app.services.ai_service.AIService._compress_image")
async def test_image_to_list_triggers_compression(
    mock_compress, mock_cls, client: AsyncClient, auth_headers: dict
):
    """When base64 image exceeds MAX_API_IMAGE_SIZE, _compress_image is called."""
    from app.services.ai_service import MAX_API_IMAGE_SIZE

    mock_cls.return_value = _make_mock_anthropic()
    # _compress_image should return small JPEG bytes so the flow continues
    small_jpeg = _make_test_image(50, 50)
    mock_compress.return_value = (small_jpeg, "image/jpeg")

    fid = await create_family_with_member(client, auth_headers)

    # Create a large enough image so its base64 exceeds MAX_API_IMAGE_SIZE
    # base64 expands by ~4/3, so we need raw bytes > MAX_API_IMAGE_SIZE * 3/4
    large_image = b"\xff\xd8\xff\xe0" + b"\x00" * (MAX_API_IMAGE_SIZE + 100)

    resp = await client.post(
        f"/v1/families/{fid}/ai/image-to-list",
        headers=auth_headers,
        files={"image": ("big.jpg", large_image, "image/jpeg")},
    )
    assert resp.status_code == 200
    mock_compress.assert_called_once()
