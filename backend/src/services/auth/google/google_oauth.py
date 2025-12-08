# src/services/auth/google/google_oauth.py
import os
import json
from datetime import datetime, timedelta, timezone
from google_auth_oauthlib.flow import Flow
from extensions import db
from src.database.models import UserToken
from src.services.auth.utils.token_crypto import encrypt_token
from dotenv import load_dotenv

# Importar Redis y uuid4 para el manejo seguro del state
from redis import Redis
from uuid import uuid4

# Cargar variables de entorno
load_dotenv()
if os.getenv("ENV") == "dev":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIS_URL = os.getenv("REDIS_URL")

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.readonly",
]


PROVIDER_NAME = "google_calendar"

# Inicializar cliente Redis (usando from_url es seguro para entornos de producción)
# Se inicializa globalmente y se conecta al usarse por primera vez.
redis_client = Redis.from_url(REDIS_URL)

# -----------------------------------------------------
# 1) Crear el Flow desde variables de entorno
# -----------------------------------------------------
# Simplifica la función get_flow - ya no necesitas el cliente personalizado
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
    Inicia el flujo OAuth. user_id proviene del JWT de Clerk (g.user_id).
    Genera un 'state', lo guarda en Redis vinculado al user_id, y lo retorna.
    """
    # Construimos la URI de redirección completa que Google espera
    redirect_uri = f"{backend_base_url}/api/v1/auth/google/callback" 
    flow = get_flow(redirect_uri)
    
    # 1. Generar STATE único
    state = str(uuid4())
    
    # 2. Guardar STATE en Redis (TTL de 5 minutos = 300 segundos)
    # Valor: El user_id de Clerk que inició el flujo
    # La clave en Redis es el STATE.
    redis_client.setex(state, 300, user_id)
    
    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true",
        state=state # Importante: Pasar el state generado manualmente
    )
    
    return auth_url, state

# -----------------------------------------------------
# 3) Callback: Guardar solo tokens, validar State
# -----------------------------------------------------
def handle_google_callback(authorization_response_url: str):
    """
    user_id viene desde Clerk (parámetro de consulta).
    Valida el 'state' y procesa la respuesta.
    """
    # 1. Extraer 'state' de la URL de respuesta
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(authorization_response_url)
    query_params = parse_qs(parsed_url.query)
    
    state = query_params.get("state", [None])[0]
    
    if not state:
        raise Exception("Missing 'state' parameter in callback URL.")
        
    # 2. Obtener el user_id de Redis usando el 'state'
    redis_user_id_bytes = redis_client.get(state)
    
    # 3. Eliminar el 'state' inmediatamente (solo se debe usar una vez)
    redis_client.delete(state)
    
    if not redis_user_id_bytes:
        # El state expiró o no existe. Esto cubre el CSRF si el atacante no conoce el state.
        raise Exception("Invalid or expired OAuth state (CSRF detected or time limit exceeded).")
    
    # Decodificar el user_id de Redis (Redis lo guarda como bytes)
    user_id = redis_user_id_bytes.decode('utf-8')
    
    # 5. Obtener el redirect_uri real de la URL de respuesta
    # Reconstruimos la URI de callback hasta la ruta (sin query params como code o state)
    parsed_auth_url = urlparse(authorization_response_url)
    callback_base = parsed_auth_url.scheme + "://" + parsed_auth_url.netloc + parsed_auth_url.path
    
    # Creamos el flow con la URI de callback que Google usó
    
    flow = get_flow(callback_base)
    flow.fetch_token(authorization_response=authorization_response_url)

    credentials = flow.credentials

    # ... (Resto de la lógica de guardar tokens cifrados se mantiene igual) ...
    # Tokens cifrados
    access_token = encrypt_token(credentials.token)
    refresh_token = encrypt_token(credentials.refresh_token) if credentials.refresh_token else None

    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=credentials.expiry.timestamp())
        if credentials.expiry
        else None
    )

    # Guardar/actualizar token
    token = UserToken.query.filter_by(user_id=user_id, provider=PROVIDER_NAME).first()

    if token:
        token.access_token = access_token
        token.refresh_token = refresh_token
        token.expires_at = expires_at
        token.updated_at = datetime.now(timezone.utc)
    else:
        db.session.add(UserToken(
            user_id=user_id,
            provider=PROVIDER_NAME,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        ))

    db.session.commit()

    return user_id 