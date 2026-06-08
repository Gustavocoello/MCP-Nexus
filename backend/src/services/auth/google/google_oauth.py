# src/services/auth/google/google_oauth.py
import os
import json
from datetime import timedelta
from urllib.parse import urlparse, parse_qs
from uuid import uuid4
from dotenv import load_dotenv

from google_auth_oauthlib.flow import Flow

from src.core.time_helper import get_now
from src.database.models.models import UserToken
from src.database.settings.connection import SessionLocal
from src.services.auth.utils.token_crypto import encrypt_token
from src.core.logging import get_logger

# ¡Importamos el Redis que ya configuramos antes!
from src.services.cache.redis_client import redis_client

logger = get_logger(__name__)
load_dotenv()

if os.getenv("ENV") == "dev":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = "1"
    
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar"
]

PROVIDER_NAME = "google_calendar"

# -----------------------------------------------------
# 1) Crear el Flow desde variables de entorno
# -----------------------------------------------------
def get_flow(redirect_uri: str):
    client_config = json.loads(os.getenv("GOOGLE_CLIENT_SECRET_JSON", "{}"))
    if not client_config:
        raise Exception("Falta GOOGLE_CLIENT_SECRET_JSON en las variables de entorno")
    
    flow = Flow.from_client_config(
        client_config,
        scopes=GOOGLE_SCOPES,
        redirect_uri=redirect_uri
    )
    flow.oauth2session.scope = set(GOOGLE_SCOPES)
    return flow

# -----------------------------------------------------
# 2) Iniciar OAuth (con Redis State)
# -----------------------------------------------------
def start_google_oauth(user_id: str, backend_base_url: str):
    """
    Inicia el flujo OAuth. user_id proviene del JWT de Clerk.
    Genera un 'state', lo guarda en Redis vinculado al user_id, y lo retorna.
    """
    redirect_uri = f"{backend_base_url}/api/v1/auth/google/callback" 
    flow = get_flow(redirect_uri)
    
    # 1. Generar STATE único
    state = str(uuid4())
    
    # 2. Guardar STATE en Redis (TTL de 5 minutos = 300 segundos)
    # Reutilizamos tu cliente de Upstash. El método 'set' acepta ttl.
    redis_client.set(state, user_id, ttl=300)
    
    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true",
        state=state 
    )
    
    return auth_url, state

# -----------------------------------------------------
# 3) Callback: Guardar solo tokens, validar State
# -----------------------------------------------------
def handle_google_callback(authorization_response_url: str):
    """
    Valida el 'state' usando Redis y procesa la respuesta de Google.
    """
    db_session = SessionLocal()
    try:
        # 1. Extraer 'state' de la URL de respuesta
        parsed_url = urlparse(authorization_response_url)
        query_params = parse_qs(parsed_url.query)
        
        state = query_params.get("state", [None])[0]
        
        if not state:
            raise Exception("Missing 'state' parameter in callback URL.")
            
        # 2. Obtener el user_id de Redis usando el 'state'
        user_id = redis_client.get(state)
        
        # 3. Eliminar el 'state' inmediatamente (protección CSRF)
        redis_client.delete(state)
        
        if not user_id:
            raise Exception("Invalid or expired OAuth state (CSRF detected or time limit exceeded).")
        
        # 4. Obtener el redirect_uri real de la URL de respuesta
        callback_base = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
        
        # 5. Intercambiar código por tokens
        flow = get_flow(callback_base)
        flow.fetch_token(authorization_response=authorization_response_url)

        credentials = flow.credentials

        # 6. Tokens cifrados
        access_token = encrypt_token(credentials.token)
        refresh_token = encrypt_token(credentials.refresh_token) if credentials.refresh_token else None

        expires_at = (
            get_now() + timedelta(seconds=credentials.expiry.timestamp())
            if credentials.expiry
            else None
        )

        # 7. Guardar/actualizar token en la BD
        token = db_session.query(UserToken).filter(
            UserToken.user_id == user_id, 
            UserToken.provider == PROVIDER_NAME
        ).first()

        if token:
            token.access_token = access_token
            token.refresh_token = refresh_token
            token.expires_at = expires_at
            token.updated_at = get_now()
        else:
            new_token = UserToken(
                user_id=user_id,
                provider=PROVIDER_NAME,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at
            )
            db_session.add(new_token)

        db_session.commit()
        return user_id

    except Exception as e:
        db_session.rollback()
        logger.exception("Error processing Google OAuth callback")
        raise Exception(f"Error processing Google OAuth callback: {str(e)}")
    finally:
        db_session.close()