# src/services/auth/clerk_middleware.py (Restaurado a PyJWT)
import os
import requests
import jwt
import time
from datetime import datetime, timezone
from functools import wraps
from flask import request, jsonify, g
from src.config.time_helper import get_now
from src.services.auth.clerk.clerk_user_sync import sync_clerk_user
from dotenv import load_dotenv

load_dotenv()

# La URL de JWKS que nos proporcionaste
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL") 
CLERK_DOMAIN = os.getenv("CLERK_DOMAIN")  # El dominio base

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


def clerk_required(f):
    """
    Decorator para rutas protegidas. 
    Valida el JWT de Clerk usando PyJWT y las JWKS.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return jsonify({"error": "Authorization header missing"}), 401

        try:
            scheme, token = auth_header.split()
            if scheme.lower() != 'bearer':
                return jsonify({"error": "Authorization scheme must be Bearer"}), 401
            
            jwks = get_clerk_jwks()

            # Obtener el key ID (kid) del header del token
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            # Buscar la clave pública correspondiente
            signing_key = next(
                key for key in jwks["keys"] if key["kid"] == kid
            )
            if not signing_key:
                return jsonify({"error": "Signing key not found"}), 401
            # Decodificación y Validación
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(signing_key)
            
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                leeway=60,
                options={
                    "verify_signature": True, 
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_aud": False, # Desactivamos la verificación de 'aud' por defecto, a menos que se defina
                    "verify_iss": False,
                }
            )
            
            clerk_id = payload.get("sub")
            if not clerk_id:
                return jsonify({"error": "JWT missing 'sub' claim"}), 401
            # Sincronizamos (Busca en DB o crea uno nuevo)
            user_obj = sync_clerk_user(clerk_id)
            #print(f"AUTH SUCCESS: Clerk:{clerk_id} -> DB_UUID:{user_obj.id}")
                        
            g.user_id = user_obj.id # Este es el ID de nuestra DB, no el de Clerk
            g.user_obj = user_obj   # Guardamos el objeto completo para evitar consultas repetidas
            g.clerk_id = clerk_id   # Este es el ID de Clerk, por si lo necesitas para otras cosas
            
            print(f"DEBUG: Hora del Servidor: {get_now().timestamp()}")
            header = jwt.get_unverified_header(token)

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidSignatureError:
            return jsonify({"error": "Invalid signature"}), 401
        except jwt.InvalidIssuerError as e:
            # Debug para ver qué issuer está viniendo
            print(f"Invalid issuer error: {e}")
            return jsonify({"error": f"Invalid issuer: {str(e)}"}), 401
        except Exception as e:
            # Añade este print para ver el error real en la consola de tu terminal/Flask
            print(f"ERROR CRÍTICO EN MIDDLEWARE: {type(e).__name__} - {str(e)}")
            import traceback
            traceback.print_exc() # Esto te dirá la línea exacta del fallo
            
            return jsonify({
                "error": "Authentication failed",
                "details": str(e)
            }), 401
            
        return f(*args, **kwargs)
        
    return decorated