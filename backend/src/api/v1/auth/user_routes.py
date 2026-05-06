# src/api/v1/user_routes.py

from flask import Blueprint, jsonify, g
from sqlalchemy import select
from src.services.auth.auth.auth_middleware import auth_required
from src.services.auth.auth.user_sync import sync_user_universal
from src.database.config.connection import SessionLocal
from src.database.models.models import UserToken
from extensions import db

user_bp = Blueprint('user', __name__, url_prefix='/api/v1/user')
integrations_bp = Blueprint("integrations", __name__, url_prefix="/api/v1/integrations")
# Ruta de sincronización
@user_bp.route("/sync", methods=["GET"])
@auth_required
def sync_user_profile():
    """
    Ruta diseñada para ser llamada inmediatamente después del login en el frontend.
    Su única función es sincronizar el perfil de Clerk con la DB local.
    """
    user = g.user_obj
    
    return jsonify({
        "status": "success",
        "message": "User profile is active.",
        "user_id": str(user.id), # Este es el UUID
        "email": user.email
    }), 200
    
@user_bp.route("/profile", methods=["GET"])
@auth_required
def get_user_profile():
    """
    Retorna los datos completos del usuario desde la DB local 
    para alimentar el componente Config/GeneralTab del SDK.
    """
    user = g.user_obj  # g.user_obj ya viene lleno gracias al middleware
    
    return jsonify({
        "id": str(user.id),
        "email": user.email,
        "fullName": user.name,
        "imageUrl": user.picture,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }), 200
    
    
@integrations_bp.route("/status", methods=["GET"])
@auth_required
def get_integration_status():
    db_session = SessionLocal()
    try:
        user_id = g.user_id

        # Verificar si existe un token de Google Calendar
        stmt = select(UserToken).filter_by(user_id=user_id, provider="google_calendar")
        google_token = db_session.execute(stmt).scalar_one_or_none()

        return jsonify({
            "google_calendar": google_token is not None
        }), 200
    finally:
        db_session.close()

@integrations_bp.route("/disconnect/<provider>", methods=["POST"])
@auth_required
def disconnect_integration(provider):
    db_session = SessionLocal()
    try:
        user_id = g.user_id

        stmt = select(UserToken).filter_by(user_id=user_id, provider=provider)
        token = db_session.execute(stmt).scalar_one_or_none()

        if not token:
            return jsonify({"message": "Integration already disconnected"}), 200

        db_session.delete(token)
        db_session.commit()

        return jsonify({"message": f"{provider} disconnected successfully"}), 200
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()