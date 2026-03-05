"""add_google_auth_to_users

Revision ID: 94cc1709f720
Revises: c4d5e6f7g8h9
Create Date: 2026-03-05 14:36:37.374644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94cc1709f720'
down_revision: Union[str, None] = 'c4d5e6f7g8h9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('auth_provider', sa.String(length=20), nullable=False, server_default='local'))
    op.add_column('users', sa.Column('google_sub', sa.String(length=255), nullable=True))
    op.alter_column('users', 'password_hash',
               existing_type=sa.VARCHAR(length=128),
               nullable=True)
    op.create_index(op.f('ix_users_google_sub'), 'users', ['google_sub'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_google_sub'), table_name='users')
    op.alter_column('users', 'password_hash',
               existing_type=sa.VARCHAR(length=128),
               nullable=False)
    op.drop_column('users', 'google_sub')
    op.drop_column('users', 'auth_provider')
