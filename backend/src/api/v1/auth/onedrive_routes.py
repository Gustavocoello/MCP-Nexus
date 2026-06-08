# src/api/v1/auth/onedrive_routes.py
import os
from urllib.parse import urlencode
from datetime import timedelta
import httpx  # <-- El reemplazo asíncrono y moderno de 'requests'

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from src.core.time_helper import get_now
from src.core.logging import get_logger
from src.database.models.models import UserToken, User
from src.database.settings.connection import get_db

logger = get_logger(__name__)
load_dotenv()

# Inicializamos el APIRouter
onedrive_router = APIRouter(prefix="/api/onedrive", tags=["OneDrive Integration"])

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ONEDRIVE_REDIRECT_URI")
ONEDRIVE_AUTHORITY = os.getenv("ONEDRIVE_AUTHORITY", "https://login.microsoftonline.com/common")
TENANT_ID = "common"
SCOPE = os.getenv("ONEDRIVE_SCOPES", "")

# ==========================================
# 1. INICIAR EL FLUJO OAUTH
# ==========================================
@onedrive_router.get("/login")
async def onedrive_login(
    # FastAPI lee el query param ?user_id=... automáticamente
    user_id: str = Query(None, description="El UUID interno del usuario")
):
    """
    Redirige al usuario a la página de login de Microsoft.
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error: Se requiere user_id para vincular la cuenta. (Uso: /login?user_id=ID)"
        )
        
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": " ".join(SCOPE.split()),  # asegura espacios normales
        "state": user_id  # Guardamos el UUID aquí. Microsoft nos lo devolverá.
    }

    auth_url = f"{ONEDRIVE_AUTHORITY}/oauth2/v2.0/authorize?{urlencode(params)}"
    logger.info(f"Redirigiendo a Microsoft Auth para el usuario: {user_id}")
    
    # RedirectResponse es nativo de FastAPI
    return RedirectResponse(url=auth_url)


# ==========================================
# 2. CALLBACK DE MICROSOFT
# ==========================================
@onedrive_router.get("/callback")
async def callback(
    code: str = Query(None),
    state: str = Query(None), # Este es el user_id que enviamos en el paso anterior
    db: Session = Depends(get_db)
):
    """
    Ruta a la que Microsoft redirige después de un login exitoso.
    No requiere autenticación JWT porque es llamada por el navegador vía redirección.
    """
    try:
        if not code or not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Faltan parámetros 'code' o 'state' en la respuesta de Microsoft."
            )
        
        user_uuid = state # Extraemos el UUID que guardamos en el login
        
        # 1. Verificamos que el usuario realmente existe en nuestra DB local
        stmt_user = select(User).filter_by(id=user_uuid)
        internal_user = db.execute(stmt_user).scalar_one_or_none()

        if not internal_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Error: El usuario con ID {user_uuid} no existe en la DB local."
            )

        # 2. Intercambiar el código por el Access Token (ASÍNCRONO)
        token_url = f"{ONEDRIVE_AUTHORITY}/oauth2/v2.0/token"
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE
        }
        
        # Usamos httpx.AsyncClient para no bloquear el hilo principal
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=data)
            
            if resp.status_code != 200:
                logger.error(f"Error en Microsoft Token URL: {resp.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Error al obtener token de Microsoft."
                )
                
            token_data = resp.json()

        # 3. Guardar o actualizar el token en nuestra DB
        stmt_token = select(UserToken).filter_by(user_id=internal_user.id, provider="onedrive")
        user_token = db.execute(stmt_token).scalar_one_or_none()
        
        expires_at = get_now() + timedelta(seconds=token_data.get("expires_in", 3600))

        if user_token:
            user_token.access_token = token_data["access_token"]
            if "refresh_token" in token_data:
                user_token.refresh_token = token_data["refresh_token"]
            user_token.expires_at = expires_at
        else:
            new_token = UserToken(
                user_id=internal_user.id,
                provider="onedrive",
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_at=expires_at
            )
            db.add(new_token)

        db.commit()
        
        # Opcionalmente, aquí puedes hacer un RedirectResponse hacia tu frontend
        # return RedirectResponse(url="https://tu-frontend.com/settings/integrations?status=success")
        
        return {"message": "Login successful! Tu cuenta de OneDrive está vinculada."}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error en callback de OneDrive")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Ocurrió un error interno durante la vinculación."
        )