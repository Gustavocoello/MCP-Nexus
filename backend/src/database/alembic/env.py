import os
import sys
import urllib.parse
from pathlib import Path
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine
from dotenv import load_dotenv

# --- Cargar entorno ---
load_dotenv()

# --- Fix sys.path para imports ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

# --- Importa modelos y metadata ---
from src.database.models import *
from extensions import db

# Alembic Config
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Metadata de modelos ---
target_metadata = db.metadata
print("🧠 Tablas activas para Alembic:", db.metadata.tables.keys())

# --- Importa los engines directamente ---
from src.database.config.mysql_config import get_mysql_engine
from src.database.config.azure_config import get_azure_engine

# --- Funciones de migración ---
def run_migrations_online():
    engines = {
        "MYSQL": get_mysql_engine(),
        "AZURE": get_azure_engine()
    }

    for label, engine in engines.items():
        with engine.connect() as connection:
            print(f"\n🚀 Ejecutando migraciones para: {label}")
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                render_as_batch=True,
                include_object=lambda obj, name, type_, reflected, compare_to:
                    not (type_ == "table" and compare_to is None)  # evita DROP de tablas nuevas
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
