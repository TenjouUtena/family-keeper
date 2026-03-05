from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.family_member import FamilyMember
    from app.models.invite_code import InviteCode


class Family(Base):
    __tablename__ = "families"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_role_name: Mapped[str] = mapped_column(String(50), nullable=False, default="Parent")
    child_role_name: Mapped[str] = mapped_column(String(50), nullable=False, default="Child")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    members: Mapped[list[FamilyMember]] = relationship(
        "FamilyMember", back_populates="family", cascade="all, delete-orphan"
    )
    invite_codes: Mapped[list[InviteCode]] = relationship(
        "InviteCode", back_populates="family", cascade="all, delete-orphan"
    )
