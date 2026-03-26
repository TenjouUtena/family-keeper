from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserListPosition(Base):
    __tablename__ = "user_list_positions"
    __table_args__ = (
        UniqueConstraint("user_id", "list_id", name="uq_user_list_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    list_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("family_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
