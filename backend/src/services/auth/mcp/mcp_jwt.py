import os
import jwt
from sqlalchemy import select
from typing import Optional, Dict, Any
from src.config.time_helper import get_now
from datetime import datetime, timedelta, timezone

from src.database.models.models import UserToken
from src.database.config.connection import SessionLocal # Usar tu conexión manual
from src.services.auth.utils.token_crypto import decrypt_token

MCP_SECRET_KEY = os.getenv("MCP_SECRET_KEY")
JWT_ALGORITHM = "HS256"

def generate_mcp_jwt(user_id: str, provider: str) -> Optional[str]:
    """
    user_id: Ahora debe ser el UUID interno (g.user_id).
    """
    if not MCP_SECRET_KEY:
        print("ERROR: MCP_SECRET_KEY no está definida.")
        return None

    db_session = SessionLocal()
    try:
        # 1. Buscar usando la sintaxis 2.0 y el UUID
        stmt = select(UserToken).filter_by(user_id=user_id, provider=provider)
        token_entry = db_session.execute(stmt).scalar_one_or_none()
        
        if not token_entry:
            print(f"Advertencia: No se encontró token para {user_id} en {provider}")
            return None

        # 2. Desencriptar
        main_token = decrypt_token(token_entry.access_token)
        
        # 3. Payload
        # Nota: 'sub' ahora llevará el UUID. El servidor MCP debe usar este ID para 
        # cualquier respuesta que deba persistirse.
        expiration = get_now() + timedelta(minutes=5)
        
        payload: Dict[str, Any] = {
            "exp": expiration,
            "iat": get_now(),
            "sub": str(user_id), 
            "provider": provider
        }
        if provider == "google_calendar":
            payload["google_access_token"] = main_token
            # Desencriptar refresh token solo si existe
            if token_entry.refresh_token:
                payload["google_refresh_token"] = decrypt_token(token_entry.refresh_token)
        
        elif provider == "notion":
            # Para Notion, el access_token es tu "Internal Integration Secret"
            payload["notion_token"] = main_token
        
        # 4. Firmar
        return jwt.encode(payload, MCP_SECRET_KEY, algorithm=JWT_ALGORITHM)

    except Exception as e:
        print(f"Error al generar el JWT para MCP: {e}")
        return None
    finally:
        db_session.close() 