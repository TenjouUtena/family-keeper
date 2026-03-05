import uuid

import boto3
from botocore.config import Config as BotoConfig
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import FamilyList, FamilyMember, ItemAttachment, ListItem, User
from app.schemas.lists import AttachmentResponse

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Pre-signed URL expiry
UPLOAD_URL_EXPIRY = 600  # 10 minutes


def _get_s3_client():
    endpoint = (
        f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=BotoConfig(
            signature_version="s3v4",
            region_name="auto",
        ),
    )


class StorageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_upload_url(
        self,
        list_id: uuid.UUID,
        item_id: uuid.UUID,
        filename: str,
        mime_type: str,
        file_size_bytes: int,
        is_completion_photo: bool,
        member: FamilyMember,
        user: User,
    ) -> dict:
        # Validate MIME type
        if mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {mime_type}",
            )

        # Validate file size
        if file_size_bytes > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large (max 10 MB)",
            )

        # Verify item belongs to list and list belongs to family
        item = await self.db.get(ListItem, item_id)
        if not item or item.list_id != list_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )

        family_list = await self.db.get(FamilyList, list_id)
        if not family_list or family_list.family_id != member.family_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this family",
            )

        # Generate storage key
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
        storage_key = (
            f"families/{member.family_id}"
            f"/lists/{list_id}"
            f"/items/{item_id}"
            f"/{uuid.uuid4()}.{ext}"
        )

        # Create attachment record (pending upload)
        attachment = ItemAttachment(
            item_id=item_id,
            storage_key=storage_key,
            filename=filename,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            is_completion_photo=is_completion_photo,
            uploaded_by=user.id,
        )
        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)

        # Generate pre-signed PUT URL
        s3 = _get_s3_client()
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.R2_BUCKET_NAME,
                "Key": storage_key,
                "ContentType": mime_type,
                "ContentLength": file_size_bytes,
            },
            ExpiresIn=UPLOAD_URL_EXPIRY,
        )

        return {
            "upload_url": upload_url,
            "attachment_id": str(attachment.id),
            "storage_key": storage_key,
            "expires_in": UPLOAD_URL_EXPIRY,
        }

    async def confirm_upload(
        self,
        item_id: uuid.UUID,
        attachment_id: uuid.UUID,
        member: FamilyMember,
    ) -> AttachmentResponse:
        attachment = await self.db.get(ItemAttachment, attachment_id)
        if not attachment or attachment.item_id != item_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment not found",
            )

        # Verify the object exists in R2
        s3 = _get_s3_client()
        try:
            s3.head_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=attachment.storage_key,
            )
        except s3.exceptions.ClientError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File not found in storage",
            )

        return AttachmentResponse.model_validate(attachment)

    async def get_download_url(
        self, storage_key: str
    ) -> str:
        s3 = _get_s3_client()
        return s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.R2_BUCKET_NAME,
                "Key": storage_key,
            },
            ExpiresIn=3600,  # 1 hour
        )
