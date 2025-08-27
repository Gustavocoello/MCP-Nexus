"""fix document.user_id length

Revision ID: 9df3677fbf90
Revises: ffc58cc1037f
Create Date: 2025-08-25 13:29:31.771432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '9df3677fbf90'
down_revision: Union[str, Sequence[str], None] = 'ffc58cc1037f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade():
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.Integer, nullable=False),
        sa.Column('url', sa.String(255), nullable=False),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('tag', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=datetime.utcnow),
        sa.Column('user_id', sa.String(64), sa.ForeignKey('users.id'), nullable=False)
    )


def downgrade():
    op.drop_table('documents')