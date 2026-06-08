import os
import sys
from pathlib import Path
from sqlalchemy import func 
from dotenv import load_dotenv

# --- Tu Helper de Tiempo ---
current_dir = Path(__file__).resolve().parent.parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

# Ajusta estos imports según la ruta real
from src.database.settings.connection import SessionLocal
from src.database.models.models import UserToken
from src.services.auth.utils.token_crypto import encrypt_token

load_dotenv()

def inyectar_token_prueba():
    user_id = os.getenv("USUARIO_TEST")
    github_token = os.getenv("GITHUB_TOKEN")

    if not user_id or not github_token:
        print("Error: Faltan las variables USUARIO_TEST o GITHUB_TOKEN en el .env")
        return

    db = SessionLocal()
    try:
        # Buscamos si ya existe
        existing = db.query(UserToken).filter_by(user_id=user_id, provider="github").first()
        
        # Encriptamos el token antes de guardarlo
        encrypted_token = encrypt_token(github_token)

        if existing:
            existing.access_token = encrypted_token
            print(f"✅ Token de GitHub actualizado para el usuario {user_id}")
        else:
            max_id = db.query(func.max(UserToken.id)).scalar() or 0
            nuevo_id = max_id + 1
            
            new_token = UserToken(
                id=nuevo_id, 
                user_id=user_id,
                provider="github",
                access_token=encrypted_token,
                refresh_token=None
            )
            db.add(new_token)
            print(f"✅ Nuevo token de GitHub insertado con ID {nuevo_id} para el usuario {user_id}")
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f" Error al insertar en BD: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inyectar_token_prueba()