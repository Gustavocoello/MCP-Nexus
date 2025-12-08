"""Migración a Clerk: Ajuste de ID de usuario y AuthProvider

Revision ID: 68ead648f165
Revises: da3cee6a9570
Create Date: 2025-11-27 23:23:23.350585

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '68ead648f165'
down_revision: Union[str, Sequence[str], None] = 'da3cee6a9570'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # 1. 🛑 ELIMINAR CLAVES FORÁNEAS (PASO NECESARIO EN AZURE SQL)
    op.drop_constraint('fk_user_token_user_id', 'user_token', type_='foreignkey')
    op.drop_constraint('fk_chat_user_id', 'chat', type_='foreignkey')
    op.drop_constraint('fk_documents_user_id', 'documents', type_='foreignkey') # Nombre de FK de documents

    # 2. ✏️ MODIFICAR LA COLUMNA users.id (Clave Primaria)
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('id',
                              existing_type=sa.VARCHAR(length=64),
                              type_=sa.String(length=255),
                              existing_nullable=False)
    
    # 3. 🔑 MODIFICAR COLUMNAS FORÁNEAS (DEBEN COINCIDIR CON users.id)
    # Columna user_token.user_id
    with op.batch_alter_table('user_token', schema=None) as batch_op:
        batch_op.alter_column('user_id',
                              existing_type=sa.VARCHAR(length=64),
                              type_=sa.String(length=255),
                              existing_nullable=False)

    # Columna chat.user_id
    with op.batch_alter_table('chat', schema=None) as batch_op:
        batch_op.alter_column('user_id',
                              existing_type=sa.VARCHAR(length=64),
                              type_=sa.String(length=255),
                              existing_nullable=True) # Mantenemos nullable=True si lo era
                              
    # Columna documents.user_id
    with op.batch_alter_table('documents', schema=None) as batch_op:
        # Nota: El log mostró que documents.user_id iba de 36 a 64, ¡pero debe ir a 255 ahora!
        batch_op.alter_column('user_id',
                              existing_type=sa.VARCHAR(length=64), # O 36 si el tipo actual es ese
                              type_=sa.String(length=255),
                              existing_nullable=False)

    # 4. ➕ RE-CREAR CLAVES FORÁNEAS
    op.create_foreign_key('fk_user_token_user_id', 'user_token', 'users', ['user_id'], ['id'])
    op.create_foreign_key('fk_chat_user_id', 'chat', 'users', ['user_id'], ['id'])
    op.create_foreign_key('fk_documents_user_id', 'documents', 'users', ['user_id'], ['id'])

    # 5. 🔠 ACTUALIZAR ENUM (Esto debe hacerse fuera del batch_alter_table si Alembic no lo generó)
    # op.execute("ALTER TABLE users MODIFY auth_provider ENUM('local', 'google', 'github', 'clerk') NOT NULL;")

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema (También debe revertir el cambio de longitud de las FKs)."""
    
    # 1. 🛑 ELIMINAR CLAVES FORÁNEAS
    op.drop_constraint('fk_user_token_user_id', 'user_token', type_='foreignkey')
    op.drop_constraint('fk_chat_user_id', 'chat', type_='foreignkey')
    op.drop_constraint('fk_documents_user_id', 'documents', type_='foreignkey')

    # 2. ↩️ REVERTIR COLUMNAS FORÁNEAS A 64 (O el tamaño original)
    with op.batch_alter_table('user_token', schema=None) as batch_op:
        batch_op.alter_column('user_id',
                              existing_type=sa.String(length=255),
                              type_=sa.VARCHAR(length=64),
                              existing_nullable=False)

    with op.batch_alter_table('chat', schema=None) as batch_op:
        batch_op.alter_column('user_id',
                              existing_type=sa.String(length=255),
                              type_=sa.VARCHAR(length=64),
                              existing_nullable=True)

    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.alter_column('user_id',
                              existing_type=sa.String(length=255),
                              type_=sa.VARCHAR(length=64), # Usa la longitud de downgrade que sea correcta (36 o 64)
                              existing_nullable=False)
                              
    # 3. ↩️ REVERTIR COLUMNA users.id
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('id',
                              existing_type=sa.String(length=255),
                              type_=sa.VARCHAR(length=64, collation='SQL_Latin1_General_CP1_CI_AS'),
                              existing_nullable=False)

    # 4. ➕ RE-CREAR CLAVES FORÁNEAS (Usando el tamaño original)
    op.create_foreign_key('fk_user_token_user_id', 'user_token', 'users', ['user_id'], ['id'])
    op.create_foreign_key('fk_chat_user_id', 'chat', 'users', ['user_id'], ['id'])
    op.create_foreign_key('fk_documents_user_id', 'documents', 'users', ['user_id'], ['id'])
    
    # 5. 🔠 ELIMINAR VALOR CLERK del ENUM
    # Esto es complejo en SQL, si lo tienes implementado, déjalo. Si no, omítelo por ahora.
    # ### end Alembic commands ###