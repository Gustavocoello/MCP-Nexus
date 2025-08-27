"""descripcion_de_cambios

Revision ID: 4b6ad253fe3d
Revises: ee23bcc65f20
Create Date: 2025-08-25 13:14:53.881565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b6ad253fe3d'
down_revision: Union[str, Sequence[str], None] = 'ee23bcc65f20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("url", sa.String(255), nullable=False),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("tag", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
    )


def downgrade():
    op.drop_table("documents")
