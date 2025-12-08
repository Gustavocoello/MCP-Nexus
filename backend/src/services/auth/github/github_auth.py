from re import A
from flask_login import login_user
import requests
from flask import redirect, request, session, url_for
from urllib.parse import urlencode
from src.database.models.models import User, AuthProvider
from extensions import db
from dotenv import load_dotenv
import os

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_API = "https://api.github.com/user"

def github_login():
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "scope": "read:user user:email",
    }
    return redirect(f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}")

def github_callback():
    code = request.args.get("code")
    if not code:
        return redirect("/login?error=missing_code")

    # Intercambio por token
    token_resp = requests.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
        }
    ).json()

    access_token = token_resp.get("access_token")
    if not access_token:
        return redirect("/login?error=token")

    # Obtener usuario
    user_resp = requests.get(
        GITHUB_USER_API,
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    github_id = user_resp["id"]
    email = user_resp.get("email") or f"{github_id}@github.fake"
    name = user_resp.get("name", "GitHub User")

    # Buscar o crear usuario
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email,
                    name=name,
                    auth_provider=AuthProvider.GITHUB.value,)
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(f"{FRONTEND_URL}/")
