# services/auth/google_oauth.py

import os
from pathlib import Path
from extensions import db
from dotenv import load_dotenv
from google.oauth2 import id_token
from src.database.models import User
from datetime import datetime, timedelta
from src.database.models import UserToken, AuthProvider
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from flask import session, request, url_for, redirect
from src.services.auth.token_crypto import encrypt_token
from google.auth.transport import requests as google_requests

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid", "email", "profile"
]

# Puedes hacer esto dinámico luego si agregas más proveedores
PROVIDER_NAME = "google_calendar"
CREDENTIALS_PATH = Path("src/config/credentials/credentials_google_calendar.json")


def get_flow():
    return Flow.from_client_secrets_file(
        str(CREDENTIALS_PATH), 
        scopes=GOOGLE_SCOPES,
        redirect_uri=url_for('google_auth.callback', _external=True)
    )


def start_google_oauth():
    flow = get_flow()
    auth_url, state = flow.authorization_url(
        prompt='consent',
        access_type='offline',
        include_granted_scopes='true'
    )
    session['oauth_state'] = state
    return redirect(auth_url)


def handle_google_callback():
    state = session.get('oauth_state')
    if not state:
        raise Exception("Falta 'state' en la sesión")

    flow = get_flow()
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials

    # Obtener email desde el id_token
    info = id_token.verify_oauth2_token(
        credentials.id_token,
        google_requests.Request(),
        os.getenv("GOOGLE_CLIENT_ID")
    )
    email = info.get("email")
    if not email:
        raise Exception("Email no encontrado en token de Google")
    google_id = info.get("sub")
    name = info.get("name")
    picture = info.get("picture")
    locale = info.get("locale")
    email_verified = info.get("email_verified")


    # Buscar o crear usuario
    user = User.query.filter_by(google_id=google_id).first()

    if not user:
        # fallback: buscar por email (solo si no hay google_id aún)
        user = User.query.filter_by(email=email).first()

    if not user:
        user = User(
            email=email,
            name=name,
            google_id=google_id,
            picture=picture,
            locale=locale,
            email_verified=email_verified,
            auth_provider=AuthProvider.GOOGLE.value
        )
        db.session.add(user)
    else:
        # opcional: actualizar si no está seteado
        if not user.google_id:
            user.google_id = google_id
        if not user.picture:
            user.picture = picture
        user.auth_provider = AuthProvider.GOOGLE.value

    db.session.commit()


    # Guardar tokens si quieres usar Calendar API
    access_token = encrypt_token(credentials.token)
    refresh_token = encrypt_token(credentials.refresh_token) if credentials.refresh_token else None
    expires_at = datetime.utcnow() + timedelta(seconds=credentials.expiry.timestamp()) if credentials.expiry else None

    from src.database.models import UserToken
    existing = UserToken.query.filter_by(user_id=user.id, provider=PROVIDER_NAME).first()
    if existing:
        existing.access_token = access_token
        existing.refresh_token = refresh_token
        existing.expires_at = expires_at
        existing.updated_at = datetime.utcnow()
    else:
        new_token = UserToken(
            user_id=user.id,
            provider=PROVIDER_NAME,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        db.session.add(new_token)

    db.session.commit()

    return user  # <- Para que `login_user(user)` lo reciba en la ruta
