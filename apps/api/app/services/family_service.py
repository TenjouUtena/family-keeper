import secrets
import string
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Family, FamilyMember, FamilyRole, InviteCode, User
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


def _generate_invite_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    # Remove ambiguous chars (0, O, I, 1, L)
    for ch in "0OI1L":
        alphabet = alphabet.replace(ch, "")
    return "".join(secrets.choice(alphabet) for _ in range(8))


class FamilyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_family(self, data: CreateFamilyRequest, user: User) -> FamilyResponse:
        family = Family(name=data.name)
        self.db.add(family)
        await self.db.flush()

        member = FamilyMember(
            family_id=family.id,
            user_id=user.id,
            role=FamilyRole.PARENT,
            is_admin=True,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(family)

        return FamilyResponse(
            id=family.id,
            name=family.name,
            parent_role_name=family.parent_role_name,
            child_role_name=family.child_role_name,
            created_at=family.created_at,
            updated_at=family.updated_at,
            member_count=1,
        )

    async def list_families(self, user: User) -> list[FamilyResponse]:
        result = await self.db.execute(
            select(Family, func.count(FamilyMember.id).label("member_count"))
            .join(FamilyMember, Family.id == FamilyMember.family_id)
            .where(
                Family.id.in_(
                    select(FamilyMember.family_id).where(FamilyMember.user_id == user.id)
                )
            )
            .group_by(Family.id)
        )
        rows = result.all()
        return [
            FamilyResponse(
                id=family.id,
                name=family.name,
                parent_role_name=family.parent_role_name,
                child_role_name=family.child_role_name,
                created_at=family.created_at,
                updated_at=family.updated_at,
                member_count=count,
            )
            for family, count in rows
        ]

    async def get_family(self, family_id: UUID) -> FamilyDetailResponse:
        result = await self.db.execute(
            select(Family)
            .options(selectinload(Family.members).selectinload(FamilyMember.user))
            .where(Family.id == family_id)
        )
        family = result.scalar_one_or_none()
        if not family:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")

        members = [
            FamilyMemberResponse(
                id=m.id,
                user_id=m.user_id,
                username=m.user.username,
                email=m.user.email,
                avatar_url=m.user.avatar_url,
                role=m.role.value,
                is_admin=m.is_admin,
                joined_at=m.joined_at,
            )
            for m in family.members
        ]

        return FamilyDetailResponse(
            id=family.id,
            name=family.name,
            parent_role_name=family.parent_role_name,
            child_role_name=family.child_role_name,
            created_at=family.created_at,
            updated_at=family.updated_at,
            member_count=len(members),
            members=members,
        )

    async def update_family(self, family_id: UUID, data: UpdateFamilyRequest) -> FamilyResponse:
        family = await self.db.get(Family, family_id)
        if not family:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(family, field, value)

        await self.db.commit()
        await self.db.refresh(family)

        count_result = await self.db.execute(
            select(func.count()).where(FamilyMember.family_id == family_id)
        )
        member_count = count_result.scalar_one()

        return FamilyResponse(
            id=family.id,
            name=family.name,
            parent_role_name=family.parent_role_name,
            child_role_name=family.child_role_name,
            created_at=family.created_at,
            updated_at=family.updated_at,
            member_count=member_count,
        )

    async def create_invite(
        self, family_id: UUID, data: CreateInviteRequest, user: User
    ) -> InviteCodeResponse:
        code = _generate_invite_code()

        # Ensure uniqueness
        existing = await self.db.scalar(select(InviteCode).where(InviteCode.code == code))
        while existing:
            code = _generate_invite_code()
            existing = await self.db.scalar(select(InviteCode).where(InviteCode.code == code))

        invite = InviteCode(
            code=code,
            family_id=family_id,
            created_by=user.id,
            expires_at=datetime.now(UTC) + timedelta(hours=data.expires_in_hours),
            max_uses=data.max_uses,
        )
        self.db.add(invite)
        await self.db.commit()
        await self.db.refresh(invite)

        return InviteCodeResponse.model_validate(invite)

    async def revoke_invite(self, family_id: UUID, code: str) -> None:
        result = await self.db.execute(
            select(InviteCode).where(
                InviteCode.family_id == family_id,
                InviteCode.code == code,
            )
        )
        invite = result.scalar_one_or_none()
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invite code not found",
            )

        invite.is_active = False
        await self.db.commit()

    async def join_family(self, data: JoinFamilyRequest, user: User) -> FamilyResponse:
        result = await self.db.execute(
            select(InviteCode).where(InviteCode.code == data.code.upper())
        )
        invite = result.scalar_one_or_none()

        if not invite or not invite.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite code")

        if invite.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite code expired",
            )

        if invite.use_count >= invite.max_uses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite code fully used",
            )

        # Check if already a member
        existing = await self.db.scalar(
            select(FamilyMember).where(
                FamilyMember.family_id == invite.family_id,
                FamilyMember.user_id == user.id,
            )
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member")

        member = FamilyMember(
            family_id=invite.family_id,
            user_id=user.id,
            role=FamilyRole.CHILD,
            is_admin=False,
        )
        self.db.add(member)
        invite.use_count += 1
        await self.db.commit()

        # Return family info
        family = await self.db.get(Family, invite.family_id)
        count_result = await self.db.execute(
            select(func.count()).where(FamilyMember.family_id == invite.family_id)
        )
        member_count = count_result.scalar_one()

        return FamilyResponse(
            id=family.id,
            name=family.name,
            parent_role_name=family.parent_role_name,
            child_role_name=family.child_role_name,
            created_at=family.created_at,
            updated_at=family.updated_at,
            member_count=member_count,
        )

    async def update_member_role(
        self, family_id: UUID, user_id: UUID, data: UpdateMemberRoleRequest
    ) -> FamilyMemberResponse:
        result = await self.db.execute(
            select(FamilyMember)
            .options(selectinload(FamilyMember.user))
            .where(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        member.role = FamilyRole(data.role)
        if data.is_admin is not None:
            member.is_admin = data.is_admin

        await self.db.commit()
        await self.db.refresh(member)

        return FamilyMemberResponse(
            id=member.id,
            user_id=member.user_id,
            username=member.user.username,
            email=member.user.email,
            avatar_url=member.user.avatar_url,
            role=member.role.value,
            is_admin=member.is_admin,
            joined_at=member.joined_at,
        )

    async def remove_member(self, family_id: UUID, user_id: UUID, current_user: User) -> None:
        result = await self.db.execute(
            select(FamilyMember).where(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        # Prevent removing yourself if you're the last admin
        if member.user_id == current_user.id and member.is_admin:
            admin_count = await self.db.scalar(
                select(func.count()).where(
                    FamilyMember.family_id == family_id,
                    FamilyMember.is_admin.is_(True),
                )
            )
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last admin",
                )

        await self.db.delete(member)
        await self.db.commit()
