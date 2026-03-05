from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


# --- Helpers ---


async def setup_list_with_item(
    client: AsyncClient, auth_headers: dict
) -> tuple[str, str, str]:
    """Create family + list + item, return (family_id, list_id, item_id)."""
    fam = await client.post(
        "/v1/families", json={"name": "Test"}, headers=auth_headers
    )
    fid = fam.json()["id"]

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

    return fid, lid, iid


def mock_s3():
    """Return a mock S3 client."""
    mock = MagicMock()
    mock.generate_presigned_url.return_value = (
        "https://fake-r2.example.com/upload?signed=true"
    )
    mock.head_object.return_value = {"ContentLength": 1024}
    mock.exceptions.ClientError = Exception
    return mock


# --- Upload URL ---


@patch("app.services.storage_service._get_s3_client")
async def test_get_upload_url(
    mock_get_client: MagicMock,
    client: AsyncClient,
    auth_headers: dict,
):
    mock_get_client.return_value = mock_s3()
    fid, lid, iid = await setup_list_with_item(
        client, auth_headers
    )

    resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}"
        f"/items/{iid}/attachments/upload-url",
        json={
            "filename": "photo.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 500_000,
            "is_completion_photo": True,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "upload_url" in data
    assert data["attachment_id"]
    assert data["storage_key"].endswith(".jpg")
    assert data["expires_in"] == 600


@patch("app.services.storage_service._get_s3_client")
async def test_upload_url_invalid_mime(
    mock_get_client: MagicMock,
    client: AsyncClient,
    auth_headers: dict,
):
    mock_get_client.return_value = mock_s3()
    fid, lid, iid = await setup_list_with_item(
        client, auth_headers
    )

    resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}"
        f"/items/{iid}/attachments/upload-url",
        json={
            "filename": "doc.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 1000,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Unsupported" in resp.json()["detail"]


async def test_upload_url_file_too_large(
    client: AsyncClient, auth_headers: dict
):
    fid, lid, iid = await setup_list_with_item(
        client, auth_headers
    )

    resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}"
        f"/items/{iid}/attachments/upload-url",
        json={
            "filename": "huge.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 20_000_000,
        },
        headers=auth_headers,
    )
    # Pydantic validation rejects > 10MB
    assert resp.status_code == 422


# --- Confirm Upload ---


@patch("app.services.storage_service._get_s3_client")
async def test_confirm_upload(
    mock_get_client: MagicMock,
    client: AsyncClient,
    auth_headers: dict,
):
    s3_mock = mock_s3()
    mock_get_client.return_value = s3_mock
    fid, lid, iid = await setup_list_with_item(
        client, auth_headers
    )

    # Get upload URL
    url_resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}"
        f"/items/{iid}/attachments/upload-url",
        json={
            "filename": "proof.png",
            "mime_type": "image/png",
            "file_size_bytes": 200_000,
            "is_completion_photo": True,
        },
        headers=auth_headers,
    )
    att_id = url_resp.json()["attachment_id"]

    # Confirm
    resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}"
        f"/items/{iid}/attachments/{att_id}/confirm",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "proof.png"
    assert data["is_completion_photo"] is True


@patch("app.services.storage_service._get_s3_client")
async def test_confirm_upload_file_missing(
    mock_get_client: MagicMock,
    client: AsyncClient,
    auth_headers: dict,
):
    s3_mock = mock_s3()
    s3_mock.head_object.side_effect = Exception("NoSuchKey")
    mock_get_client.return_value = s3_mock

    fid, lid, iid = await setup_list_with_item(
        client, auth_headers
    )

    # Get upload URL
    url_resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}"
        f"/items/{iid}/attachments/upload-url",
        json={
            "filename": "missing.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 1000,
        },
        headers=auth_headers,
    )
    att_id = url_resp.json()["attachment_id"]

    # Confirm without actually uploading
    resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}"
        f"/items/{iid}/attachments/{att_id}/confirm",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()


# --- Photo completion + upload flow ---


@patch("app.services.storage_service._get_s3_client")
async def test_photo_completion_with_upload(
    mock_get_client: MagicMock,
    client: AsyncClient,
    auth_headers: dict,
):
    """After uploading a completion photo, marking done should succeed."""
    s3_mock = mock_s3()
    mock_get_client.return_value = s3_mock

    fam = await client.post(
        "/v1/families", json={"name": "Photo Test"}, headers=auth_headers
    )
    fid = fam.json()["id"]

    lst = await client.post(
        f"/v1/families/{fid}/lists",
        json={
            "name": "Chores",
            "list_type": "chores",
            "require_photo_completion": True,
        },
        headers=auth_headers,
    )
    lid = lst.json()["id"]

    items = await client.post(
        f"/v1/families/{fid}/lists/{lid}/items",
        json={"items": [{"content": "Wash dishes"}]},
        headers=auth_headers,
    )
    iid = items.json()[0]["id"]

    # Without photo: should fail
    resp = await client.patch(
        f"/v1/families/{fid}/lists/{lid}/items/{iid}",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Upload completion photo
    url_resp = await client.post(
        f"/v1/families/{fid}/lists/{lid}"
        f"/items/{iid}/attachments/upload-url",
        json={
            "filename": "proof.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 100_000,
            "is_completion_photo": True,
        },
        headers=auth_headers,
    )
    att_id = url_resp.json()["attachment_id"]

    # Confirm upload
    await client.post(
        f"/v1/families/{fid}/lists/{lid}"
        f"/items/{iid}/attachments/{att_id}/confirm",
        headers=auth_headers,
    )

    # Now marking done should succeed
    resp = await client.patch(
        f"/v1/families/{fid}/lists/{lid}/items/{iid}",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
