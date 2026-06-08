import os
import jwt
import time
import requests
from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.time_helper import get_now
from src.services.auth.auth.user_sync import CLERK_API_URL, sync_user_universal
# Asumo que importas AuthProvider de donde correspondía en tus modelos
from src.database.models.models import AuthProvider
from dotenv import load_dotenv

load_dotenv()

CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL") 
CLERK_DOMAIN = os.getenv("CLERK_DOMAIN")
MANUAL_JWT_SECRET = os.getenv("BACKEND_JWT_SECRET")

# Cache para las JWKS
cached_jwks = None
cached_jwks_expiry = 0

def get_clerk_jwks():
    """Obtiene y cachea las JWKS de Clerk."""
    global cached_jwks, cached_jwks_expiry
    
    if cached_jwks and cached_jwks_expiry > time.time():
        return cached_jwks

    if not CLERK_JWKS_URL:
        jwks_url = f"https://{CLERK_DOMAIN}/.well-known/jwks.json"
    else:
        jwks_url = CLERK_JWKS_URL
    
    try:
        response = requests.get(jwks_url)
        response.raise_for_status()
        jwks = response.json()
        
        cached_jwks = jwks
        cached_jwks_expiry = time.time() + 3600
        return jwks
    except requests.RequestException as e:
        print(f"Error al obtener JWKS de Clerk: {e}")
        if cached_jwks:
            return cached_jwks
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="No se pudo conectar a Clerk para obtener las claves de autenticación."
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error procesando JWKS: {e}")

# ==========================================
# LA MAGIA DE FASTAPI: DEPENDENCIA DE AUTH
# ==========================================

# Esto le dice a FastAPI que esta ruta requiere un Token Bearer
security = HTTPBearer()

def get_current_user(
    # FastAPI extrae y valida el "Bearer Token" automáticamente
    credentials: HTTPAuthorizationCredentials = Depends(security),
    # FastAPI extrae el header automáticamente (con valor por defecto)
    x_project_origin: str = Header(default="jarvis-default", alias="X-Project-Origin")
) -> dict:
    """
    Dependencia que valida el token y retorna los datos del usuario.
    Reemplaza a @auth_required y al objeto 'g' de Flask.
    """
    token = credentials.credentials
    app_id = x_project_origin
    
    payload = None
    provider = None

    CLERK_APP_ID = ['jarvis-platform', 'jarvis-default'] 
    AWS_APP_IDS = ["tu-app-aws"] 

    try:
        # CASO A: CLERK (Portafolio)
        if app_id in CLERK_APP_ID:
            provider = AuthProvider.CLERK
            jwks = get_clerk_jwks()
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            signing_key = next((key for key in jwks["keys"] if key["kid"] == kid), None)
            if not signing_key:
                raise Exception("No se encontró la llave pública (kid) en Clerk.")
                
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(signing_key)
            payload = jwt.decode(
                token, public_key, algorithms=["RS256"], 
                options={"verify_aud": False, "verify_iss": False}, leeway=30
            )
        
        # CASO B: Developing (AWS)
        elif app_id in AWS_APP_IDS:
            provider = AuthProvider.AWS
            # Lógica de AWS...
            pass
        
        # CASO C: MANUAL 
        else:
            provider = AuthProvider.MANUAL
            if not MANUAL_JWT_SECRET:
                raise Exception("MANUAL_JWT_SECRET no configurado en el servidor.")
            
            payload = jwt.decode(
                token, MANUAL_JWT_SECRET, algorithms=["HS256"],  
                options={ "verify_aud": False, "verify_iss": False }, leeway=30
            )
            
        # --- EXTRACCIÓN Y SINCRONIZACIÓN ---
        provider_user_id = payload.get("sub")
        
        if not provider_user_id:
            raise Exception("Token missing subject (sub)")

        # Sincronizamos el usuario en la DB 
        # (Asumo que esta función maneja su propia sesión de BD internamente)
        user_obj = sync_user_universal(
            provider_user_id=provider_user_id,
            app_id=app_id,
            provider=provider,
            extra_data=payload
        )

        print(f"[AUTH SUCCESS] User: {user_obj.email} | App: {app_id} | Provider: {provider}")

        # EN LUGAR DE "g.user_id = user_obj.id", RETORNAMOS UN DICCIONARIO
        return {
            "user_id": user_obj.id,
            "app_id": app_id,
            "user_obj": user_obj 
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        print(f"[AUTH FATAL ERROR] {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )