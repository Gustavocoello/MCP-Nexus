"""Change url column to Text

Revision ID: 26e5f0c5ddb0
Revises: 9df3677fbf90
Create Date: 2025-08-26 14:41:11.521290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '26e5f0c5ddb0'
down_revision: Union[str, Sequence[str], None] = '9df3677fbf90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_foreign_key(
        "fk_documents_user_id",
        "documents", "users",
        ["user_id"], ["id"]
    )

def downgrade():
    op.drop_constraint("fk_documents_user_id", "documents", type_="foreignkey")