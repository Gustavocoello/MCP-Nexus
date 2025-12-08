"""add_clerk_enum_manual

Revision ID: aeeedcd329c9
Revises: be6957a57897
Create Date: 2025-11-28 23:23:04.731992

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aeeedcd329c9'
down_revision: Union[str, Sequence[str], None] = 'be6957a57897'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
