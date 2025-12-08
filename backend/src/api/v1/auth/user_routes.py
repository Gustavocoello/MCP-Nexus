# src/api/v1/user_routes.py

from flask import Blueprint, jsonify, g
from src.services.auth.clerk.clerk_middleware import clerk_required
from src.services.auth.clerk.clerk_user_sync import sync_clerk_user
from src.database.models.models import UserToken
from extensions import db

user_bp = Blueprint('user', __name__, url_prefix='/api/v1/user')
integrations_bp = Blueprint("integrations", __name__, url_prefix="/api/v1/integrations")
# Ruta de sincronización
@user_bp.route("/sync", methods=["GET"])
@clerk_required
def sync_user_profile():
    """
    Ruta diseñada para ser llamada inmediatamente después del login en el frontend.
    Su única función es sincronizar el perfil de Clerk con la DB local.
    """
    clerk_user_id = g.user_id
    
    try:
        # Llama a la función que verifica si existe y lo crea si no.
        local_user = sync_clerk_user(clerk_user_id) 
        
        # Opcional: Puedes devolver los datos del usuario local
        return jsonify({
            "status": "success",
            "message": "User profile synchronized successfully.",
            "user_id": local_user.id,
            "email": local_user.email
        }), 200
        
    except Exception as e:
        # Si la sincronización falla (ej. error de conexión a la API de Clerk)
        return jsonify({"error": f"Failed to sync user profile: {str(e)}"}), 500
    
    
@integrations_bp.route("/status", methods=["GET"])
@clerk_required
def get_integration_status():
    user_id = g.user_id

    # Verificar si existe un token de Google Calendar
    google_token = UserToken.query.filter_by(
        user_id=user_id,
        provider="google_calendar"
    ).first()

    return jsonify({
        "google_calendar": google_token is not None
    }), 200

@integrations_bp.route("/disconnect/<provider>", methods=["POST"])
@clerk_required
def disconnect_integration(provider):
    user_id = g.user_id

    token = UserToken.query.filter_by(
        user_id=user_id,
        provider=provider
    ).first()

    if not token:
        return jsonify({"message": "Integration already disconnected"}), 200

    db.session.delete(token)
    db.session.commit()

    return jsonify({"message": f"{provider} disconnected successfully"}), 200