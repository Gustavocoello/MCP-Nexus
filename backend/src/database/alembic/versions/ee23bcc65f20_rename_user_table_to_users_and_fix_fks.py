"""rename user table to users and fix FKs

Revision ID: ee23bcc65f20
Revises: 20f3318ab750
Create Date: 2025-07-11 07:51:31.757681
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ee23bcc65f20'
down_revision: Union[str, Sequence[str], None] = '20f3318ab750'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Rename table 'user' to 'users' and fix FKs."""

    # 👇 Primero renombrar la tabla
    op.rename_table('user', 'users')

    # 👇 Luego arreglar FKs
    with op.batch_alter_table('chat') as batch_op:
        batch_op.drop_constraint('FK__chat__user_id__0A9D95DB', type_='foreignkey')
        batch_op.create_foreign_key('fk_chat_user_id', 'users', ['user_id'], ['id'])

    with op.batch_alter_table('user_token') as batch_op:
        batch_op.drop_constraint('FK__user_toke__user___3D2915A8', type_='foreignkey')
        batch_op.create_foreign_key('fk_user_token_user_id', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema: Revert table rename and FKs to 'user'."""

    # 👇 Primero revertir los FKs
    with op.batch_alter_table('user_token') as batch_op:
        batch_op.drop_constraint('fk_user_token_user_id', type_='foreignkey')
        batch_op.create_foreign_key('FK__user_toke__user___3D2915A8', 'user', ['user_id'], ['id'])

    with op.batch_alter_table('chat') as batch_op:
        batch_op.drop_constraint('fk_chat_user_id', type_='foreignkey')
        batch_op.create_foreign_key('FK__chat__user_id__0A9D95DB', 'user', ['user_id'], ['id'])

    # 👇 Finalmente renombrar de vuelta la tabla
    op.rename_table('users', 'user')
