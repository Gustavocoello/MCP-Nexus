"""Add login fields to user table

Revision ID: df6bfd3eaf49
Revises: d7136f3c3d75
Create Date: 2025-07-01 12:50:40.214158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df6bfd3eaf49'
down_revision: Union[str, Sequence[str], None] = 'd7136f3c3d75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.add_column('user', sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.sql.expression.true()))
    op.add_column('user', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('last_login', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('user', 'last_login')
    op.drop_column('user', 'created_at')
    op.drop_column('user', 'is_active')
    op.drop_column('user', 'password_hash')
