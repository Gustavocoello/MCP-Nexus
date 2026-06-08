import os
import requests
from sqlalchemy import select
from datetime import timedelta, timezone

from src.core.logging import get_logger
from src.core.time_helper import get_now
from src.database.models.models import UserToken
from src.database.settings.connection import SessionLocal
from dotenv import load_dotenv

# Importamos nuestro cliente de Redis centralizado
from src.services.cache.redis_client import redis_client

logger = get_logger(__name__)
load_dotenv()

DRIVE_ID = os.getenv("ONEDRIVE_DRIVE_ID") 

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
SCOPE = "https://graph.microsoft.com/.default"

# ==========================================
# 1. SUBIR ARCHIVO A ONEDRIVE
# ==========================================
def upload_to_onedrive(access_token: str, filename: str, file_bytes: bytes) -> str:
    """
    Sube un archivo a OneDrive.
    Esta función es sincrónica, pero es segura porque FastAPI la ejecuta 
    dentro de un BackgroundTask (Threadpool) sin bloquear el servidor.
    """
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/Datos adjuntos/Work/Personal_Projects/MCP-Nexus/2025/{filename}:/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream"
    }
    
    resp = requests.put(url, headers=headers, data=file_bytes)
    
    if resp.status_code in [200, 201]:
        return resp.json()["@microsoft.graph.downloadUrl"]
    else:
        logger.error(f"OneDrive upload failed: {resp.text}")
        raise Exception(f"OneDrive upload failed: {resp.status_code}")


# ==========================================
# 2. TOKEN DE SERVICIO (App-Only) CON REDIS
# ==========================================
def get_onedrive_service_token() -> str:
    """
    Obtiene el token de servicio de la aplicación.
    Utiliza Redis para asegurar que todos los workers compartan el mismo token.
    """
    cache_key = "onedrive:service_token"
    
    # 1. Intentar obtener de Redis
    cached_token = redis_client.get(cache_key)
    if cached_token:
        return cached_token

    # 2. Si no hay token o expiró, pedimos uno nuevo a Microsoft
    logger.info("Solicitando nuevo Service Token a Microsoft...")
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
        "grant_type": "client_credentials",
    }

    resp = requests.post(TOKEN_URL, data=data)
    if resp.status_code != 200:
        logger.error(f"Error getting OneDrive token: {resp.text}")
        raise Exception(f"Error getting OneDrive token: {resp.status_code}")

    token_data = resp.json()
    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600)

    # 3. Guardar en Redis (Le restamos 60 seg al TTL para refrescarlo antes de que expire)
    safe_ttl = max(10, expires_in - 60)
    redis_client.set(cache_key, access_token, ttl=safe_ttl)

    return access_token


# ==========================================
# 3. TOKEN DE USUARIO (Delegated)
# ==========================================
def get_user_onedrive_token(user_id: str) -> str:
    """
    Obtiene el token de acceso de un usuario, refrescándolo si es necesario.
    Maneja su propia db_session porque puede ser llamado desde hilos en segundo plano.
    """
    db_session = SessionLocal()
    try:
        stmt = select(UserToken).filter_by(user_id=user_id, provider="onedrive")
        user_token = db_session.execute(stmt).scalar_one_or_none()
        
        if not user_token:
            raise Exception("El usuario no ha vinculado su cuenta de OneDrive")

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