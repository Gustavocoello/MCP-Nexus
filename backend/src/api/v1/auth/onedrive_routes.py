# src/services/integrations/onedrive.py
from flask import Blueprint, redirect, request
import os
import requests
from flask import g
from sqlalchemy import select
from extensions import db
from dotenv import load_dotenv
from urllib.parse import urlencode
from src.config.time_helper import get_now
from datetime import datetime, timedelta, timezone
from src.database.models.models import UserToken, User
from src.database.config.connection import SessionLocal
from src.services.auth.clerk.clerk_middleware import clerk_required
from src.config.logging_config import get_logger

logger = get_logger(__name__)

load_dotenv()

onedrive_bp = Blueprint("onedrive", __name__)

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ONEDRIVE_REDIRECT_URI")
TENANT_ID = "common"  # para cuentas personales
SCOPE = os.getenv("ONEDRIVE_SCOPES")

@onedrive_bp.route("/login")

def onedrive_login():
    user_id = request.args.get("user_id")
    if not user_id:
        return "Error: Se requiere user_id para vincular la cuenta. (Uso: /login?user_id=ID)", 400
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": " ".join(SCOPE.split()),  # asegura espacios normales
        "state": user_id
    }

    auth_url = f"{os.getenv('ONEDRIVE_AUTHORITY')}/oauth2/v2.0/authorize?{urlencode(params)}"
    print(f"Redirecting to: {auth_url}")
    return redirect(auth_url)


@onedrive_bp.route("/callback")

def callback():
    db_session = SessionLocal() # 1. Abrimos sesión
    try:
        code = request.args.get("code")
        # El 'state' se usa para validar, pero como tienes @clerk_required, 
        # confiamos en g.user_id que viene del JWT de Clerk.
        clerk_id_from_state = request.args.get("state") # Luego borrar solo para hacerlo desde aqui, siempre usar el g.user_id
        
        if not code:
            return "No code returned", 400
        
        stmt_user = select(User).filter_by(clerk_id=clerk_id_from_state)
        internal_user = db_session.execute(stmt_user).scalar_one_or_none()

        if not internal_user:
            return f"Error: El usuario {clerk_id_from_state} no existe en la DB local.", 404
        

        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE
        }
        
        resp = requests.post(token_url, data=data)
        if resp.status_code != 200:
            return f"Error al obtener token: {resp.text}", 400
            
        token_data = resp.json()

        # 2. Buscamos el token usando g.user_id (que ya es tu UUID interno)
        stmt_token = select(UserToken).filter_by(user_id=internal_user.id, provider="onedrive")
        user_token = db_session.execute(stmt_token).scalar_one_or_none()
        
        # Manejo de expiración coherente
        now = get_now()
        expires_at = now + timedelta(seconds=token_data.get("expires_in", 3600))

        if user_token:
            # Actualizar
            user_token.access_token = token_data["access_token"]
            if "refresh_token" in token_data:
                user_token.refresh_token = token_data["refresh_token"]
            user_token.expires_at = expires_at
        else:
            # Crear nuevo
            user_token = UserToken(
                user_id=internal_user.id, # El UUID inyectado por el middleware
                provider="onedrive",
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_at=expires_at
            )
            db_session.add(user_token)

        db_session.commit()
        return "Login successful! Tu cuenta de OneDrive está vinculada.", 200

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error en callback de OneDrive: {str(e)}")
        return "Ocurrió un error interno durante la vinculación.", 500
        
    finally:
        db_session.close()

