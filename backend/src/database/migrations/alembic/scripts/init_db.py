# backend/scripts/init_db.py
import os
import sys
from pathlib import Path
from flask import Flask
from dotenv import load_dotenv

# --- Fix Path ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from extensions import db
from src.database import models  # asegura que todos los modelos estén importados
# Cargar las variables de entorno desde el archivo .env
load_dotenv()

HOST_DB = os.getenv("ROOT_BD")
USER_DB = os.getenv("USER_BD")
PASS_DB = os.getenv("PASS_BD")
NAME_DB = os.getenv("NAME_BD")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{USER_DB}:{PASS_DB}@{HOST_DB}:3306/{NAME_DB}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
# Crea la base de datos si no existe, no utiliza Alembic
with app.app_context():
    db.create_all()
    print("🎉 Tablas creadas correctamente en MySQL.")
