# services/extensions/onedrive_service.py
import os
import time
import requests
from json import load
from extensions import db
from datetime import datetime, timedelta
from functools import lru_cache
from flask_login import login_required, current_user
from src.database.models.models import UserToken
from dotenv import load_dotenv

load_dotenv()

DRIVE_ID = os.getenv("ONEDRIVE_DRIVE_ID")  # ponlo en .env

def upload_to_onedrive(access_token, filename, file_bytes):
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/Datos adjuntos/Work/Personal_Projects/2025/{filename}:/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream"
    }
    resp = requests.put(url, headers=headers, data=file_bytes)
    if resp.status_code in [200, 201]:
        return resp.json()["@microsoft.graph.downloadUrl"]
    else:
        raise Exception(f"OneDrive upload failed: {resp.text}")



TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
SCOPE = "https://graph.microsoft.com/.default"

# cache simple en memoria
_token_cache = {"access_token": None, "expires_at": 0}

def get_onedrive_service_token():
    global _token_cache

    # Si el token aún es válido, lo devolvemos
    if _token_cache["access_token"] and _token_cache["expires_at"] > time.time():
        return _token_cache["access_token"]

    # Pedimos un token nuevo
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
        "grant_type": "client_credentials",
    }

    resp = requests.post(TOKEN_URL, data=data)
    if resp.status_code != 200:
        raise Exception(f"Error getting OneDrive token: {resp.text}")

    token_data = resp.json()
    access_token = token_data["access_token"]
    expires_in = token_data["expires_in"]

    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = time.time() + expires_in - 60  # refrescar 1 min antes

    return access_token


def get_user_onedrive_token(user_id):
    user_token = UserToken.query.filter_by(user_id=user_id, provider="onedrive").first()
    if not user_token:
        raise Exception("El usuario no ha hecho login en OneDrive aún")

    # Si expiró
    if user_token.expires_at and user_token.expires_at < datetime.utcnow():
        # Refresh token
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": user_token.refresh_token,
            "scope": SCOPE
        }
        resp = requests.post(f"https://login.microsoftonline.com/common/oauth2/v2.0/token", data=data)
        token_data = resp.json()
        user_token.access_token = token_data["access_token"]
        user_token.refresh_token = token_data.get("refresh_token", user_token.refresh_token)
        user_token.expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
        db.session.commit()

    return user_token.access_token