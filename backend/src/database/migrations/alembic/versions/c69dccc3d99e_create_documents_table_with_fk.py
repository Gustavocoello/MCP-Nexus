"""create documents table with FK

Revision ID: c69dccc3d99e
Revises: 26e5f0c5ddb0
Create Date: 2025-08-26 15:09:35.025272

"""
from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'c69dccc3d99e'
down_revision: Union[str, Sequence[str], None] = '26e5f0c5ddb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    dialect = context.get_context().dialect.name

    # Default según motor de base de datos
    if dialect == "mssql":
        created_default = sa.text("GETUTCDATE()")
    else:  # mysql u otros
        created_default = sa.text("CURRENT_TIMESTAMP")

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("tag", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=created_default, nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_documents_user_id")
    )

def downgrade():
    op.drop_table("documents")