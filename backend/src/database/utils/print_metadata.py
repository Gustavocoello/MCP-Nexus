# src/database/tools/print_metadata.py

import os
import sys
from pathlib import Path

# Setup de rutas
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from extensions import db

# Crear app falsa
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("MYSQL_URL") or (
    f"mysql+mysqlconnector://{os.getenv('USER_BD')}:{os.getenv('PASS_BD')}@{os.getenv('ROOT_BD')}:3306/{os.getenv('NAME_BD')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Importar los modelos explícitamente
with app.app_context():
    from src.database.models import User
    from src.database.models import Chat
    from src.database.models import Message
    from src.database.models import UserToken
    from src.database.models import UserMemory

    print("✅ Modelos cargados correctamente.")
    print("🧠 Tablas registradas en db.metadata:")
    for table in db.metadata.tables:
        print(f" - {table}")
