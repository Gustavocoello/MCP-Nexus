# src/services/auth/github/github_auth.py
import os
from urllib.parse import urlencode
import httpx
from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from dotenv import load_dotenv

from src.database.models.models import User, AuthProvider
from src.database.settings.connection import SessionLocal
from src.core.logging import get_logger

load_dotenv()
logger = get_logger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_API = "https://api.github.com/user"


async def github_login(request: Request):
    """Genera la URL de autorización de GitHub y redirige al usuario."""
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "scope": "read:user user:email",
    }
    url = f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
    return RedirectResponse(url=url)


async def github_callback(request: Request):
    """Maneja el retorno de GitHub, obtiene el token y crea/loguea al usuario."""
    db_session = SessionLocal()
    try:
        # En FastAPI, leemos los query parameters así:
        code = request.query_params.get("code")
        if not code:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=missing_code")

        # 1. Intercambio por token de acceso (Asíncrono con httpx)
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code,
                }
            )
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                logger.error("No se recibió access_token de GitHub")
                return RedirectResponse(url=f"{FRONTEND_URL}/login?error=token")

            # 2. Obtener datos de usuario de GitHub
            user_resp = await client.get(
                GITHUB_USER_API,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_data = user_resp.json()

        github_id = str(user_data.get("id"))
        email = user_data.get("email") or f"{github_id}@github.fake"
        name = user_data.get("name", "GitHub User")

        # 3. Buscar usuario en base de datos
        stmt = select(User).filter_by(email=email)
        user = db_session.execute(stmt).scalar_one_or_none()

        if not user:
            logger.info(f"Creando nuevo usuario vía GitHub: {email}")
            user = User(
                email=email,
                name=name,
                auth_provider=AuthProvider.GITHUB.value,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

        # NOTA: En APIs REST/FastAPI no usamos 'login_user(user)' de Flask-Login.
        # Aquí normalmente generarías un JWT y lo pasarías al frontend en la URL o Cookie.
        # Por ahora, mantenemos tu redirección original:
        return RedirectResponse(url=f"{FRONTEND_URL}/")

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error en GitHub Login: {str(e)}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=callback_failed")

    finally:
        db_session.close()
