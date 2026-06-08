from fastapi import APIRouter, Request, HTTPException
from src.services.auth.github.github_auth import github_login, github_callback
from src.core.logging import get_logger

logger = get_logger(__name__)

github_auth_router = APIRouter(prefix="/api/v1/auth/github", tags=["GitHub Auth"])

@github_auth_router.get("/login")
async def login_github(request: Request):
    """
    Inicia el flujo de autenticación con GitHub.
    """
    try:
        # Nota: Ajusta 'github_login' en tu capa de servicios para que retorne 
        # un RedirectResponse o un diccionario con la URL.
        return await github_login(request)
    except Exception as e:
        logger.exception("Error en GitHub Login")
        raise HTTPException(status_code=500, detail=str(e))


@github_auth_router.get("/callback")
async def callback_github(request: Request):
    """
    Maneja el retorno de GitHub.
    """
    try:
        # Nota: Ajusta 'github_callback' en tu capa de servicios para que no use 'flask.request'
        return await github_callback(request)
    except Exception as e:
        logger.exception("Error en GitHub Callback")
        raise HTTPException(status_code=500, detail=str(e))