# src/services/auth/mcp/mcp_jwt.py

import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

# Importaciones de la capa de Jarvis (DB y utilidades de encriptación)
from src.database.models import UserToken
from src.services.auth.utils.token_crypto import decrypt_token
from extensions import db # Asegúrate de tener db importado si lo usas fuera de la app context

# Obtén la clave secreta. Debe ser la misma que usa el MCP Server.
MCP_SECRET_KEY = os.getenv("MCP_SECRET_KEY")
JWT_ALGORITHM = "HS256"

def generate_mcp_jwt(user_id: str, provider: str) -> Optional[str]:
    """
    Busca el UserToken de Google en la DB, lo desencripta y crea un JWT
    para ser usado por el Servidor MCP.
    """
    if not MCP_SECRET_KEY:
        print("⚠️ ERROR: MCP_SECRET_KEY no está definida.")
        return None

    # 1. Buscar el token encriptado en la DB de Jarvis
    token_entry = UserToken.query.filter_by(user_id=user_id, provider=provider).first()
    
    if not token_entry:
        return None

    try:
        # 2. Desencriptar los tokens de Google
        google_access_token = decrypt_token(token_entry.access_token)
        google_refresh_token = decrypt_token(token_entry.refresh_token) if token_entry.refresh_token else None
        
        # 3. Preparar el payload del JWT (incluyendo los tokens DESENCRIPTADOS)
        expiration = datetime.now(timezone.utc) + timedelta(minutes=5) # 5 minutos de validez
        
        payload: Dict[str, Any] = {
            "exp": expiration,
            "iat": datetime.now(timezone.utc),
            "sub": str(user_id),
            "user_id": str(user_id), # Añadimos user_id para fácil acceso
            "provider": provider,
            "google_access_token": google_access_token,
        }
        
        # Añadir el refresh token solo si existe
        if google_refresh_token:
            payload["google_refresh_token"] = google_refresh_token
        
        # 4. Crear y firmar el JWT
        jwt_token = jwt.encode(payload, MCP_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        return jwt_token

    except Exception as e:
        # Manejo de errores de DB o desencriptación
        print(f"Error al generar el JWT para MCP: {e}")
        return None