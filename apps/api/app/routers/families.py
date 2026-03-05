from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.permissions import RequireFamilyAdmin, RequireFamilyMember
from app.database import get_db
from app.models import FamilyMember, FamilyRole, User
from app.schemas import MessageResponse
from app.schemas.family import (
    CreateFamilyRequest,
    CreateInviteRequest,
    FamilyDetailResponse,
    FamilyMemberResponse,
    FamilyResponse,
    InviteCodeResponse,
    JoinFamilyRequest,
    UpdateFamilyRequest,
    UpdateMemberRoleRequest,
)
from app.services.family_service import FamilyService

router = APIRouter(prefix="/v1/families", tags=["families"])


@router.post("", response_model=FamilyResponse, status_code=201)
async def create_family(
    data: CreateFamilyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FamilyService(db)
    return await service.create_family(data, current_user)


@router.get("", response_model=list[FamilyResponse])
async def list_families(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FamilyService(db)
    return await service.list_families(current_user)


@router.get("/{family_id}", response_model=FamilyDetailResponse)
async def get_family(
    family_id: UUID,
    _member: FamilyMember = Depends(RequireFamilyMember()),
    db: AsyncSession = Depends(get_db),
):
    service = FamilyService(db)
    return await service.get_family(family_id)


@router.patch("/{family_id}", response_model=FamilyResponse)
async def update_family(
    family_id: UUID,
    data: UpdateFamilyRequest,
    _member: FamilyMember = Depends(RequireFamilyAdmin()),
    db: AsyncSession = Depends(get_db),
):
    service = FamilyService(db)
    return await service.update_family(family_id, data)


@router.post("/{family_id}/invites", response_model=InviteCodeResponse, status_code=201)
async def create_invite(
    family_id: UUID,
    data: CreateInviteRequest = CreateInviteRequest(),
    _member: FamilyMember = Depends(RequireFamilyMember(role=FamilyRole.PARENT)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FamilyService(db)
    return await service.create_invite(family_id, data, current_user)


@router.delete("/{family_id}/invites/{code}", response_model=MessageResponse)
async def revoke_invite(
    family_id: UUID,
    code: str,
    _member: FamilyMember = Depends(RequireFamilyAdmin()),
    db: AsyncSession = Depends(get_db),
):
    service = FamilyService(db)
    await service.revoke_invite(family_id, code)
    return MessageResponse(message="Invite code revoked")


@router.post("/join", response_model=FamilyResponse)
async def join_family(
    data: JoinFamilyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FamilyService(db)
    return await service.join_family(data, current_user)


@router.patch("/{family_id}/members/{user_id}", response_model=FamilyMemberResponse)
async def update_member_role(
    family_id: UUID,
    user_id: UUID,
    data: UpdateMemberRoleRequest,
    _member: FamilyMember = Depends(RequireFamilyAdmin()),
    db: AsyncSession = Depends(get_db),
):
    service = FamilyService(db)
    return await service.update_member_role(family_id, user_id, data)


@router.delete("/{family_id}/members/{user_id}", response_model=MessageResponse)
async def remove_member(
    family_id: UUID,
    user_id: UUID,
    _member: FamilyMember = Depends(RequireFamilyAdmin()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FamilyService(db)
    await service.remove_member(family_id, user_id, current_user)
    return MessageResponse(message="Member removed")
