# database/migrations/migration_script.py

import sys
from pathlib import Path

# --- Fix Paths ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

# --- Imports ---
from extensions import db
from src.database.config.azure_config import get_azure_engine
from src.database.models.models import *

def run_migration():
    engine = get_azure_engine()
    print("Conexión a Azure SQL establecida correctamente")

    print("Tablas detectadas en db.metadata:")
    print(db.metadata.tables.keys())

    db.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente en Azure SQL")

if __name__ == "__main__":
    run_migration()
