"""create documents table compatible MySQL + Azure

Revision ID: 0935af340990
Revises: 9a478a3eba7c
Create Date: 2025-08-26 15:35:15.667757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '0935af340990'
down_revision: Union[str, Sequence[str], None] = '9a478a3eba7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)

    # Verifica si la tabla documents existe
    if 'documents' not in inspector.get_table_names():
        op.create_table(
            'documents',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('mime_type', sa.String(100), nullable=False),
            sa.Column('size_bytes', sa.Integer, nullable=False),
            sa.Column('url', sa.Text, nullable=False),
            sa.Column('source', sa.String(50)),
            sa.Column('tag', sa.String(50)),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column('user_id', sa.String(64), nullable=False)
        )
        op.create_foreign_key(
            'fk_documents_user_id',
            'documents',
            'users',
            ['user_id'],
            ['id']
        )
    else:
        # Si la tabla existe, solo asegura que la columna url sea Text
        op.alter_column('documents', 'url', type_=sa.Text, existing_type=sa.String(255))

def downgrade():
    conn = op.get_bind()
    inspector = inspect(conn)

    if 'documents' in inspector.get_table_names():
        op.drop_table('documents')