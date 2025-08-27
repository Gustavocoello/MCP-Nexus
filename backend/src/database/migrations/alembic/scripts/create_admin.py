# backend/scripts/create_admin.py
import os
import sys
import uuid
from pathlib import Path
from flask import Flask
from dotenv import load_dotenv

# Ajustar el path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from extensions import db
from src.database.models import User

# Cargar variables de entorno
load_dotenv()

HOST_DB = os.getenv("ROOT_BD")
USER_DB = os.getenv("USER_BD")
PASS_DB = os.getenv("PASS_BD")
NAME_DB = os.getenv("NAME_BD")

# Inicializar app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{USER_DB}:{PASS_DB}@{HOST_DB}:3306/{NAME_DB}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    # Verificar si ya hay un admin
    existing = User.query.filter_by(is_admin=True).first()
    if existing:
        print(f"Ya existe un admin: {existing.name} ({existing.id})")
    else:
        admin = User(
            id=str(uuid.uuid4()),
            name="ADMIN",
            email=None,
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin creado con ID: {admin.id}")
