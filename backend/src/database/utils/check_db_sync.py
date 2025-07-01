# database/utils/check_db_sync.py
import sys
from pathlib import Path

# --- Fix Paths ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.database.alembic.scripts.check_sync import check_sync

if __name__ == "__main__":
    check_sync()
