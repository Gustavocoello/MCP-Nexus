# src/database/alembic/scripts/check_sync.py

import os
import sys
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from pathlib import Path

# --- Fix Paths ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.database.config.mysql_config import get_mysql_engine
from src.database.config.azure_config import get_azure_engine

BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # .../src/database/utils
ALEMBIC_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))  # .../src/database


alembic_ini_path = os.path.join(ALEMBIC_DIR, "alembic.ini")
cfg = Config(alembic_ini_path)
cfg.set_main_option("script_location", str(Path(ALEMBIC_DIR).resolve()))


def check_sync():
    print("🔍 Verificando sincronización de migraciones...")

    # Config y script alembic
    print("📂 script_location:", cfg.get_main_option("script_location"))
    script = ScriptDirectory.from_config(cfg)
    head_revision = script.get_current_head()

    engines = {
        "MYSQL": get_mysql_engine(),
        "AZURE": get_azure_engine()
    }

    desincronizados = []

    for name, engine in engines.items():
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            status = "✅" if current_rev == head_revision else "❌"
            print(f"{status} {name}: {current_rev or 'None'}")

            if current_rev != head_revision:
                desincronizados.append(name)

    print()
    if desincronizados:
        print(f"⚠️ Bases desincronizadas: {', '.join(desincronizados)}")
        exit(1)
    else:
        print("🎉 Todo sincronizado. ¡Puedes dormir tranquilo!")
