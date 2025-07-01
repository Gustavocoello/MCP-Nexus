# src/database/config/legacy_config.py
import os
import uuid
import sys
from flask import Flask
from pathlib import Path
from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy import create_engine

# Ajustar el path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from extensions import db
from sqlalchemy import MetaData, Table
from src.database.models import Chat
from src.database.models import User

load_dotenv()

HOST_DB = os.getenv("ROOT_BD")
USER_DB = os.getenv("USER_BD")
PASS_DB = os.getenv("PASS_BD")
NAME_DB = os.getenv("NAME_BD")

# Migramos de la base de datos legacy a la nueva estructura
def get_legacy_engine():
    url = f"mysql+mysqlconnector://{USER_DB}:{PASS_DB}@{HOST_DB}/jarvis_legacy"
    return create_engine(url)

# Inicializar app y DB
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{os.getenv('USER_BD')}:{os.getenv('PASS_BD')}@{os.getenv('ROOT_BD')}:3306/{os.getenv('NAME_BD')}"
db.init_app(app)

legacy_engine = get_legacy_engine()

with app.app_context():
    # Obtener el admin
    admin = User.query.filter_by(is_admin=True).first()
    if not admin:
        raise Exception("⚠️ No hay usuario admin en la base actual.")

    print(f"👤 Usando Admin: {admin.id}")

    metadata = MetaData()
    metadata.reflect(bind=legacy_engine)
    legacy_chat = Table("chat", metadata, autoload_with=legacy_engine)

    with legacy_engine.connect() as conn:
        rows = conn.execute(sa.select(legacy_chat)).mappings()


        for row in rows:
            chat_id = str(row["id"]) if row["id"] else str(uuid.uuid4())
            db.session.add(Chat(
                id=chat_id,
                user_id=admin.id,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                summary=row.get("summary"),
                title=row.get("title")
            ))

    db.session.commit()
    print(f"✅ Migrados {rows} chats al usuario admin.")