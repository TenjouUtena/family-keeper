import json
from uuid import UUID

import anthropic
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import RequireFamilyMember
from app.database import get_db
from app.models import FamilyMember
from app.schemas.ai import ImageToListResponse
from app.services.ai_service import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE, AIService

router = APIRouter(tags=["ai"])


@router.post(
    "/v1/families/{family_id}/ai/image-to-list",
    response_model=ImageToListResponse,
)
async def image_to_list(
    family_id: UUID,
    image: UploadFile = File(...),
    list_type: str | None = Form(None),
    member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
):
    """Extract list items from a photo using AI vision."""
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    service = AIService()
    await service.check_rate_limit(family_id)

    try:
        result = await service.image_to_list(image_bytes, image.content_type, list_type)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Could not extract items from image")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {e}")

    return result
