"""Replace GoogleAuthToken with UserToken

Revision ID: 329f82442478
Revises: df6bfd3eaf49
Create Date: 2025-07-01 15:51:19.448152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '329f82442478'
down_revision: Union[str, Sequence[str], None] = 'df6bfd3eaf49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 👇 Elimina la tabla antigua si existe (mejor usar IF EXISTS con SQL crudo si tienes miedo de error)
    op.drop_table('google_auth_token')

    # 👇 Crea la nueva tabla escalable
    op.create_table(
        'user_token',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(length=64), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.UniqueConstraint('user_id', 'provider', name='uq_user_provider')
    )


def downgrade() -> None:
    op.drop_table('user_token')

    op.create_table(
        'google_auth_token',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(length=64), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    )