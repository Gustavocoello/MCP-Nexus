# services/extensions/onedrive_service.py
import os
import time
import requests
from extensions import db
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from src.database.models.models import UserToken
from src.database.config.connection import SessionLocal
from src.config.logging_config import get_logger
from src.config.time_helper import get_now
from dotenv import load_dotenv

# Este servicio se encarga de toda la lógica relacionada con la integración de OneDrive,
logger = get_logger(__name__)

load_dotenv()

DRIVE_ID = os.getenv("ONEDRIVE_DRIVE_ID")  # ponlo en .env

def upload_to_onedrive(access_token, filename, file_bytes):
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/Datos adjuntos/Work/Personal_Projects/MCP-Nexus/2025/{filename}:/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream"
    }
    resp = requests.put(url, headers=headers, data=file_bytes)
    if resp.status_code in [200, 201]:
        return resp.json()["@microsoft.graph.downloadUrl"]
    else:
        raise Exception(f"OneDrive upload failed: {resp.text}")



TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
SCOPE = "https://graph.microsoft.com/.default"

# cache simple en memoria
_token_cache = {"access_token": None, "expires_at": 0}

def get_onedrive_service_token():
    global _token_cache

    # Si el token aún es válido, lo devolvemos
    if _token_cache["access_token"] and _token_cache["expires_at"] > time.time():
        return _token_cache["access_token"]

    # Pedimos un token nuevo
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
        "grant_type": "client_credentials",
    }

    resp = requests.post(TOKEN_URL, data=data)
    if resp.status_code != 200:
        raise Exception(f"Error getting OneDrive token: {resp.text}")

    token_data = resp.json()
    access_token = token_data["access_token"]
    expires_in = token_data["expires_in"]

    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = time.time() + expires_in - 60  # refrescar 1 min antes

    return access_token


def get_user_onedrive_token(user_id):
    """
    Obtiene el token de acceso, refrescándolo si es necesario.
    user_id es el UUID interno del sistema.
    """
    db_session = SessionLocal()
    try:
        stmt = select(UserToken).filter_by(user_id=user_id, provider="onedrive")
        user_token = db_session.execute(stmt).scalar_one_or_none()
        
        if not user_token:
            # En lugar de solo Exception, podrías devolver None para manejarlo mejor
            raise Exception("El usuario no ha vinculado su cuenta de OneDrive")

        # Usamos timezone.utc para evitar problemas de desfase horario
        now = get_now()
        
        # Si expiró o está a punto de expirar (margen de 1 minuto)
        if user_token.expires_at and user_token.expires_at.replace(tzinfo=timezone.utc) < now + timedelta(minutes=1):
            logger.info(f"Refrescando token de OneDrive para usuario: {user_id}")
            
            data = {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": user_token.refresh_token,
                "scope": SCOPE
            }
            
            resp = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data=data)
            
            if resp.status_code == 200:
                token_data = resp.json()
                user_token.access_token = token_data["access_token"]
                
                if "refresh_token" in token_data:
                    user_token.refresh_token = token_data["refresh_token"]
                
                # Guardar nueva expiración
                expires_in = token_data.get("expires_in", 3600)
                user_token.expires_at = now + timedelta(seconds=expires_in)
                
                db_session.add(user_token)
                db_session.commit()
            else:
                logger.error(f"Error al refrescar token OneDrive: {resp.text}")
                raise Exception("Sesión de OneDrive expirada. Por favor, vincula tu cuenta de nuevo.")

        return user_token.access_token

    except Exception as e:
        db_session.rollback()
        raise e
    finally:
        db_session.close()