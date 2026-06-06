import os
import jwt
from sqlalchemy import select
from typing import Optional, Dict, Any
from src.core.time_helper import get_now
from datetime import datetime, timedelta, timezone

from src.database.models.models import UserToken
from src.database.settings.connection import SessionLocal # Usar tu conexión manual
from src.services.auth.utils.token_crypto import decrypt_token

MCP_SECRET_KEY = os.getenv("MCP_SECRET_KEY")
JWT_ALGORITHM = "HS256"

def generate_mcp_jwt(user_id: str, provider: str) -> Optional[str]:
    if not MCP_SECRET_KEY:
        print("ERROR: MCP_SECRET_KEY no está definida.")
        return None

    db_session = SessionLocal()
    try:
        expiration = get_now() + timedelta(minutes=5)
        payload: Dict[str, Any] = {
            "exp": expiration,
            "iat": get_now(),
            "sub": str(user_id),
            "provider": provider
        }

        # ── Proveedores locales: no necesitan token en DB ──
        LOCAL_PROVIDERS = {"files", "sandbox"}  # agrega aquí los que sean locales
        if provider in LOCAL_PROVIDERS:
            return jwt.encode(payload, MCP_SECRET_KEY, algorithm=JWT_ALGORITHM)

        # ── Proveedores externos: buscar token en DB ──
        stmt = select(UserToken).filter_by(user_id=user_id, provider=provider)
        token_entry = db_session.execute(stmt).scalar_one_or_none()

        if not token_entry:
            print(f"Advertencia: No se encontró token para {user_id} en {provider}")
            return None

        main_token = decrypt_token(token_entry.access_token)

        if provider == "google_calendar":
            payload["google_access_token"] = main_token
            if token_entry.refresh_token:
                payload["google_refresh_token"] = decrypt_token(token_entry.refresh_token)

        elif provider == "notion":
            payload["notion_api_key"] = main_token
        
        elif provider == "github":
            payload["github_token"] = main_token

        return jwt.encode(payload, MCP_SECRET_KEY, algorithm=JWT_ALGORITHM)

    except Exception as e:
        print(f"Error al generar el JWT para MCP: {e}")
        return None
    finally:
        db_session.close()