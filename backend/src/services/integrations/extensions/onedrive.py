from flask import Blueprint, redirect, request, session, url_for
import os
import requests
from extensions import db
from dotenv import load_dotenv
from urllib.parse import urlencode
from datetime import datetime, timedelta
from flask_login import login_required, current_user
from src.database.models.models import UserToken

load_dotenv()

onedrive_bp = Blueprint("onedrive", __name__)

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ONEDRIVE_REDIRECT_URI")
TENANT_ID = "common"  # para cuentas personales
SCOPE = os.getenv("ONEDRIVE_SCOPES")

@onedrive_bp.route("/login")
def onedrive_login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": " ".join(SCOPE.split()),  # asegura espacios normales
    }

    auth_url = f"{os.getenv('ONEDRIVE_AUTHORITY')}/oauth2/v2.0/authorize?{urlencode(params)}"
    print(f"Redirecting to: {auth_url}")
    return redirect(auth_url)


@onedrive_bp.route("/callback")
@login_required
def callback():
    code = request.args.get("code")
    if not code:
        return "No code returned", 400

    token_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE
    }
    resp = requests.post(token_url, data=data)
    token_data = resp.json()

    # Guardamos en DB
    user_token = UserToken.query.filter_by(user_id=current_user.id, provider="onedrive").first()
    expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
    if user_token:
        user_token.access_token = token_data["access_token"]
        user_token.refresh_token = token_data.get("refresh_token")
        user_token.expires_at = expires_at
    else:
        user_token = UserToken(
            user_id=current_user.id,
            provider="onedrive",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=expires_at
        )
        db.session.add(user_token)

    db.session.commit()
    return "Login successful! Ahora ya puedes subir archivos automáticamente."

