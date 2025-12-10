# src/api/v1/auths/google_routes.py

from flask import Blueprint, redirect, request, jsonify, g
from src.services.auth.google.google_oauth import start_google_oauth, handle_google_callback
from src.services.auth.clerk.clerk_middleware import clerk_required
from src.services.auth.clerk.clerk_user_sync import sync_clerk_user
from src.config.logging_config import get_logger
from dotenv import load_dotenv
import os 

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL")
BACKEND_URL = os.getenv("BACKEND_URL")

google_auth_bp = Blueprint("google_auth", __name__, url_prefix="/api/v1/auth/google")

# Configurar logger
logger = get_logger(__name__)

# 1) Login: Ruta protegida por Clerk JWT
@google_auth_bp.route("/login")
@clerk_required 
def login():
    user_id = g.get("user_id") 
    
    if not user_id:
        return jsonify({"error": "Authentication required (Clerk JWT missing or invalid)"}), 401

    # 1. Sincronizar/Crear el perfil de usuario en la DB local
    try:
        local_user = sync_clerk_user(clerk_user_id=user_id)
    except Exception as e:
        return jsonify({"error": f"User synchronization failed: {str(e)}"}), 500

    # OBTENEMOS LA URL BASE DINÁMICA DEL SERVIDOR (ej. http://localhost:5000)
    backend_base_url = BACKEND_URL or request.url_root.rstrip('/')
    
    auth_url, state = start_google_oauth(
        user_id=local_user.id,
        backend_base_url=backend_base_url # <-- Pasamos la base de la URL
    )
     
    return jsonify({
        "auth_url": auth_url,
        "state": state
    })

# 2) Callback: Ruta que recibe la respuesta de Google
@google_auth_bp.route("/callback")
def callback():
    user_id_from_redis = None
    
    try:
        # El state viene en el query param de Google 
        state_param = request.args.get("state")
        
        if not state_param:
            # Notar que ya no se espera el 'userId' aquí
            return jsonify({"error": "Missing state parameter in OAuth callback"}), 400

        full_url = request.url
        
        # handle_google_callback extrae el userId de Redis
        user_id_from_redis = handle_google_callback(
            authorization_response_url=full_url
        )
        
        # Redirige al frontend, ahora pasando el userId extraído de Redis
        return redirect(f"{FRONTEND_URL}/c/{user_id_from_redis}/settings")
        
    except Exception as e:
        # Captura errores de State/CSRF o cualquier error interno
        logger.error(f"Google OAuth Callback Error: {e}")
        
        # ✅ CORREGIDO: Si user_id_from_redis es None, redirigir a una ruta genérica
        if user_id_from_redis:
            error_url = f"{FRONTEND_URL}/c/{user_id_from_redis}/settings?error=oauth_failed&details={str(e)}"
        else:
            # Si no tenemos user_id, redirigir a una página de error genérica
            error_url = f"{FRONTEND_URL}/auth/error?error=oauth_failed&details={str(e)}"
        
        return redirect(error_url)