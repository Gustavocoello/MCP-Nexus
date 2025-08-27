"""sync existing tables

Revision ID: 9a478a3eba7c
Revises: c69dccc3d99e
Create Date: 2025-08-26 15:24:28.071623

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a478a3eba7c'
down_revision: Union[str, Sequence[str], None] = 'c69dccc3d99e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
