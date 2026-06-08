import os
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

from src.services.auth.google.google_oauth import start_google_oauth, handle_google_callback
from src.services.auth.auth.auth_middleware import get_current_user
from src.core.logging import get_logger

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL")
BACKEND_URL = os.getenv("BACKEND_URL")

logger = get_logger(__name__)

google_auth_router = APIRouter(prefix="/api/v1/auth/google", tags=["Google Auth"])

# 1) Login: Ruta protegida por Clerk JWT
@google_auth_router.get("/login")
async def login(
    request: Request, 
    user_data: dict = Depends(get_current_user) # FastAPI valida el token y sincroniza al usuario
):
    try:
        # Extraemos el UUID directamente del middleware
        user_id = str(user_data["user_id"])
        
        # OBTENEMOS LA URL BASE DINÁMICA DEL SERVIDOR
        # request.base_url en FastAPI devuelve la URL raíz (ej. http://localhost:5000/)
        backend_base_url = BACKEND_URL or str(request.base_url).rstrip('/')
        
        # Inicia el flujo de Google
        auth_url, state = start_google_oauth(
            user_id=user_id,
            backend_base_url=backend_base_url
        )
         
        return {
            "auth_url": auth_url,
            "state": state
        }
        
    except Exception as e:
        logger.exception("Error generando Google OAuth URL")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 2) Callback: Ruta que recibe la respuesta de Google
@google_auth_router.get("/callback")
async def callback(request: Request):
    user_id_from_redis = None
    
    try:
        # Extraemos el 'state' de los query parameters
        state_param = request.query_params.get("state")
        
        if not state_param:
            raise ValueError("Missing state parameter in OAuth callback")

        # FastAPI: request.url contiene la URL completa con todos los queries
        full_url = str(request.url)
        
        # (Si handle_google_callback es síncrono y pesado, idealmente usarías run_in_threadpool)
        user_id_from_redis = handle_google_callback(
            authorization_response_url=full_url
        )
        
        # Redirige al frontend exitosamente usando RedirectResponse nativo de FastAPI
        return RedirectResponse(url=f"{FRONTEND_URL}/c/{user_id_from_redis}/settings")
        
    except Exception as e:
        logger.error(f"Google OAuth Callback Error: {str(e)}")
        
        # Si ocurre un error, construimos la URL de fallback hacia el frontend
        if user_id_from_redis:
            error_url = f"{FRONTEND_URL}/c/{user_id_from_redis}/settings?error=oauth_failed&details={str(e)}"
        else:
            error_url = f"{FRONTEND_URL}/auth/error?error=oauth_failed&details={str(e)}"
        
        return RedirectResponse(url=error_url)