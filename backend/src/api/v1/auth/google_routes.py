# src/api/v1/auths/google_routes.py

from flask import Blueprint, redirect, session, request, jsonify
from src.services.auth.google_oauth import start_google_oauth, handle_google_callback
from flask_login import current_user, login_user
from dotenv import load_dotenv
import os 

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL")

google_auth_bp = Blueprint("google_auth", __name__, url_prefix="/api/v1/auth/google")

@google_auth_bp.route("/login")
def login():
    """
    Redirige al usuario a la página de login de Google.
    """
    return start_google_oauth()

@google_auth_bp.route("/callback")
def callback():
    try:
        user = handle_google_callback()  # sin argumentos
        login_user(user)
        return redirect(f"{FRONTEND_URL}/")
    except Exception as e:
        return jsonify({"error": str(e)}), 400

