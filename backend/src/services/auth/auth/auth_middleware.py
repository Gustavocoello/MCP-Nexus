# src/services/auth/clerk_middleware.py (Restaurado a PyJWT)
from asyncio.log import logger
import os
import requests
import jwt
import time
from functools import wraps
from flask import request, jsonify, g
from src.config.time_helper import get_now
from src.services.auth.auth.user_sync import CLERK_API_URL, sync_user_universal
from src.database.models import AuthProvider
from dotenv import load_dotenv

load_dotenv()

# La URL de JWKS que nos proporcionaste
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL") 
CLERK_DOMAIN = os.getenv("CLERK_DOMAIN")  # El dominio base

MANUAL_JWT_SECRET = os.getenv("BACKEND_JWT_SECRET")

# Cache para las JWKS
cached_jwks = None
cached_jwks_expiry = 0

def get_clerk_jwks():
    """Obtiene y cachea las JWKS de Clerk."""
    global cached_jwks, cached_jwks_expiry
    
    # Revisar si el caché es válido (ej. 1 hora)
    if cached_jwks and cached_jwks_expiry > time.time():
        return cached_jwks

    if not CLERK_JWKS_URL:
        # En caso de que no esté en .env, usa el valor que me diste por defecto
        # Esto solo es un fallback, la buena práctica es usar os.getenv
        jwks_url = f"https://{CLERK_DOMAIN}/.well-known/jwks.json"
    else:
        jwks_url = CLERK_JWKS_URL
    
    try:
        response = requests.get(jwks_url)
        response.raise_for_status()
        jwks = response.json()
        
        # Actualizar caché
        cached_jwks = jwks
        cached_jwks_expiry = time.time() + 3600 # Cachear por 1 hora
        return jwks

    except requests.RequestException as e:
        print(f"Error al obtener JWKS de Clerk: {e}")
        if cached_jwks:
            return cached_jwks
        raise Exception("No se pudo conectar a Clerk para obtener las claves de autenticación.")
    except Exception as e:
        raise Exception(f"Error procesando JWKS: {e}")


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        app_id = request.headers.get("X-Project-Origin", "jarvis-default") # Valor por defecto

        if not auth_header:
            return jsonify({"error": "Authorization header missing"}), 401

        try:
            scheme, token = auth_header.split()
            if scheme.lower() != 'bearer':
                return jsonify({"error": "Invalid auth scheme"}), 401

            payload = None
            provider = None

            # --- RAMIFICACIÓN DE VALIDACIÓN ---
            
            CLERK_APP_ID = ['jarvis-platform', 'jarvis-default'] 
            AWS_APP_IDS = ["tu-app-aws"] # Aquí puedes listar los app_id que correspondan a AWS u otros proveedores
            
            # CASO A: CLERK (Portafolio)
            if app_id in CLERK_APP_ID:
                provider = AuthProvider.CLERK
                jwks = get_clerk_jwks()
                header = jwt.get_unverified_header(token)
                kid = header.get("kid")
                
                signing_key = next(key for key in jwks["keys"] if key["kid"] == kid)
                if not signing_key:
                    raise Exception("No se encontró la llave pública (kid) en Clerk.")
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(signing_key)
                
                payload = jwt.decode(
                    token, public_key, algorithms=["RS256"], 
                    options={"verify_aud": False, "verify_iss": False}, leeway=30
                )
                pass
            
            # CASO B: Developing 
            elif app_id in AWS_APP_IDS: # Ejemplo para el futuro elif de AWS
                provider = AuthProvider.AWS
                # Aquí iría la validación de Cognito/AWS
                pass
            
            # CASO C: MANUAL (Tu SaaS de Contabilidad u otros)
            else:
                provider = AuthProvider.MANUAL
                if not MANUAL_JWT_SECRET:
                    raise Exception("MANUAL_JWT_SECRET no configurado en el servidor.")
                
                payload = jwt.decode(
                    token, MANUAL_JWT_SECRET, algorithms=["HS256"],  options={ "verify_aud": False, "verify_iss": False }, leeway=30
                )
                
            
            # --- EXTRACCIÓN Y SINCRONIZACIÓN ---
            
            provider_user_id = payload.get("sub")
            email = payload.get("email") # Asegúrate que tu SaaS incluya 'email' en el JWT

            if not provider_user_id:
                return jsonify({"error": "Token missing subject (sub)"}), 401

            # Llamamos al sincronizador que ya creamos
            # Si es manual, pasamos los datos que vienen en el payload (email, name, picture)
            user_obj = sync_user_universal(
                provider_user_id=provider_user_id,
                app_id=app_id,
                provider=provider,
                extra_data=payload # Pasamos todo el payload como info extra
            )

            # Inyectamos en el contexto global de Flask
            g.user_id = user_obj.id # Este es el ID de nuestra DB, no el de Clerk
            g.user_obj = user_obj   # Guardamos el objeto completo para evitar consultas repetidas
            g.app_id = app_id       # Este es el app_id que nos indica que app es

            print(f"[AUTH SUCCESS] User: {user_obj.email} | App: {app_id} | Provider: {provider}")

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except Exception as e:
            print(f"[AUTH FATAL ERROR] {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc() 
            return jsonify({
                "error": "Authentication failed", 
                "details": str(e)
                }), 401

        return f(*args, **kwargs)
    return decorated