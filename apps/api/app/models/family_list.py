from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.family import Family
    from app.models.list_item import ListItem


class ListType(str, enum.Enum):
    TODO = "todo"
    GROCERY = "grocery"
    CHORES = "chores"
    CUSTOM = "custom"


class FamilyList(Base):
    __tablename__ = "family_lists"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    list_type: Mapped[ListType] = mapped_column(
        Enum(ListType, native_enum=False),
        nullable=False,
        default=ListType.TODO,
    )
    visible_to_role: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    editable_by_role: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    require_photo_completion: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    family: Mapped[Family] = relationship("Family")
    items: Mapped[list[ListItem]] = relationship(
        "ListItem",
        back_populates="family_list",
        cascade="all, delete-orphan",
        order_by="ListItem.position",
    )
