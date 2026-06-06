import os
import sys
from pathlib import Path
from logging.config import fileConfig
from alembic import context
from dotenv import load_dotenv

# --- Cargar entorno ---
load_dotenv()

# --- Fix sys.path para imports ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

# --- Importa modelos y metadata ---
from src.database.models import *
from src.database.models.models import Base
from src.database.settings.connection import engine

# Alembic Config
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Metadata de modelos ---
target_metadata = Base.metadata
print("🧠 Tablas activas para Alembic:", Base.metadata.tables.keys())

# --- Funciones de migración ---
def run_migrations_online():
    # Usamos el engine que connection.py ya configuró (DEV o PROD)
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            # include_schemas=True # (Opcional, descomenta si usas esquemas en postgres)
        )
        with context.begin_transaction():
            context.run_migrations()

def run_migrations_offline():
    raise NotImplementedError("Solo soportamos migraciones online.")

# --- Dispatcher ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()