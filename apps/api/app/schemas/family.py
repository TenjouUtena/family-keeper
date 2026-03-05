from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateFamilyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class UpdateFamilyRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    parent_role_name: str | None = Field(None, min_length=1, max_length=50)
    child_role_name: str | None = Field(None, min_length=1, max_length=50)


class FamilyMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    username: str
    email: str
    avatar_url: str | None
    role: str
    is_admin: bool
    joined_at: datetime

    model_config = {"from_attributes": True}


class FamilyResponse(BaseModel):
    id: UUID
    name: str
    parent_role_name: str
    child_role_name: str
    created_at: datetime
    updated_at: datetime
    member_count: int

    model_config = {"from_attributes": True}


class FamilyDetailResponse(FamilyResponse):
    members: list[FamilyMemberResponse]


class CreateInviteRequest(BaseModel):
    max_uses: int = Field(default=10, ge=1, le=100)
    expires_in_hours: int = Field(default=72, ge=1, le=720)


class InviteCodeResponse(BaseModel):
    code: str
    family_id: UUID
    expires_at: datetime
    max_uses: int
    use_count: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class JoinFamilyRequest(BaseModel):
    code: str = Field(min_length=8, max_length=8)


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(pattern=r"^(parent|child)$")
    is_admin: bool | None = None
