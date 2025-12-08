"""manual_add_clerk_to_auth_provider

Revision ID: a55ecb592986
Revises: aeeedcd329c9
Create Date: 2025-11-29 07:42:24.043229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a55ecb592986'
down_revision: Union[str, Sequence[str], None] = 'aeeedcd329c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """
    Cambio aplicado manualmente:
    - MySQL: ALTER TABLE users MODIFY COLUMN auth_provider ENUM(...)
    - Azure SQL: ALTER TABLE users ALTER COLUMN auth_provider VARCHAR(20)
                 + ADD CONSTRAINT CK_users_auth_provider CHECK (...)
    
    Esta migración está vacía porque el cambio ya se hizo directamente en las bases de datos.
    """
    pass


def downgrade():
    """
    No revertir - cambio crítico aplicado manualmente.
    """
    pass
