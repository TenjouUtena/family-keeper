from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import FamilyMember, FamilyRole, User


class RequireFamilyMember:
    """FastAPI dependency that verifies the user is a member of the family.

    Usage:
        @router.get("/families/{family_id}/...")
        async def endpoint(
            member: FamilyMember = Depends(RequireFamilyMember()),
        ):

        # With role requirement:
        @router.post("/families/{family_id}/invites")
        async def endpoint(
            member: FamilyMember = Depends(RequireFamilyMember(role=FamilyRole.PARENT)),
        ):
    """

    def __init__(self, role: FamilyRole | None = None):
        self.role = role

    async def __call__(
        self,
        family_id: UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> FamilyMember:
        result = await db.execute(
            select(FamilyMember).where(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == current_user.id,
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this family",
            )

        if self.role and member.role != self.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {self.role.value} role",
            )

        return member


class RequireFamilyAdmin:
    """FastAPI dependency that verifies the user is an admin of the family.

    Usage:
        @router.patch("/families/{family_id}")
        async def endpoint(
            member: FamilyMember = Depends(RequireFamilyAdmin()),
        ):
    """

    async def __call__(
        self,
        family_id: UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> FamilyMember:
        result = await db.execute(
            select(FamilyMember).where(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == current_user.id,
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this family",
            )

        if not member.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

        return member
