from re import A
from extensions import db
import requests
from flask_login import login_user
from urllib.parse import urlencode
from flask import redirect, request, session, url_for
from src.database.models.models import User, AuthProvider
from src.database.config.connection import SessionLocal
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
    db_session = SessionLocal() # 1. Abrimos sesión
    try:
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

        # Obtener datos de usuario de GitHub
        user_resp = requests.get(
            GITHUB_USER_API,
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()

        github_id = str(user_resp["id"])
        email = user_resp.get("email") or f"{github_id}@github.fake"
        name = user_resp.get("name", "GitHub User")

        # 2. Buscar usuario usando la db_session (Sintaxis 2.0)
        from sqlalchemy import select
        stmt = select(User).filter_by(email=email)
        user = db_session.execute(stmt).scalar_one_or_none()

        if not user:
            # Aquí se creará con un UUID nuevo automáticamente si tu modelo así lo tiene
            user = User(
                email=email,
                name=name,
                auth_provider=AuthProvider.GITHUB.value,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user) # Para obtener el ID generado

        # flask-login necesita el objeto cargado
        login_user(user)
        
        return redirect(f"{FRONTEND_URL}/")

    except Exception as e:
        db_session.rollback() # 3. Si algo falla, limpiamos
        print(f"Error en GitHub Login: {e}")
        return redirect(f"{FRONTEND_URL}/login?error=callback_failed")

    finally:
        db_session.close()
