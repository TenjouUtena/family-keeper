"""create_shared_calendars

Revision ID: e6f7g8h9i0j1
Revises: d5e6f7g8h9i0
Create Date: 2026-03-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e6f7g8h9i0j1"
down_revision: Union[str, None] = "d5e6f7g8h9i0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shared_calendars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("google_calendar_id", sa.String(500), nullable=False),
        sa.Column("calendar_name", sa.String(500), nullable=False),
        sa.Column("color", sa.String(20), nullable=False, server_default="#4F46E5"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "family_id", "user_id", "google_calendar_id", name="uq_shared_calendar"
        ),
    )
    op.create_index("ix_shared_calendars_family_id", "shared_calendars", ["family_id"])
    op.create_index("ix_shared_calendars_user_id", "shared_calendars", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_shared_calendars_user_id", table_name="shared_calendars")
    op.drop_index("ix_shared_calendars_family_id", table_name="shared_calendars")
    op.drop_table("shared_calendars")
