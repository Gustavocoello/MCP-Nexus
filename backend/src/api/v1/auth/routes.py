from flask import Blueprint, request, jsonify
from flask_login import login_required, logout_user,current_user, login_user
from werkzeug.security import check_password_hash
from extensions import db
from src.database.models import AuthProvider, User
from src.services.extensions.limiter import limiter
from flask_limiter import Limiter
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from src.database.models import User, AuthProvider
from extensions import db

auth_bp = Blueprint("auth", __name__)

#----------------- LOGIN -------------------
@auth_bp.route("/api/v1/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email y contraseña requeridos"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or user.auth_provider != AuthProvider.LOCAL.value:
        return jsonify({"error": "Usuario no válido o no es local"}), 401

    if not user.check_password(password):
        return jsonify({"error": "Email o contraseña incorrectos"}), 401

    login_user(user)  # crea la sesión

    user.last_login = db.func.now()
    db.session.commit()

    return jsonify({
        "message": "Inicio de sesión exitoso",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "auth_provider": user.auth_provider,
            "picture": user.picture
        }
    }), 200

# ----------------- LOGOUT --------------------
@auth_bp.route("/api/v1/auth/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Sesión cerrada"}), 200


@auth_bp.route("/api/v1/auth/me", methods=["GET"])
@login_required
def get_current_user():
    user = current_user
    return jsonify({
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "auth_provider": user.auth_provider,
        "picture": user.picture
    }), 200

# ---------------- CHANGE PASSWORD-----------------
@auth_bp.route("/api/v1/auth/change-password", methods=["POST"])
@login_required
def change_password():
    if current_user.auth_provider != AuthProvider.LOCAL.value:
        return jsonify({"error": "Este usuario no puede cambiar contraseña porque no es local."}), 403

    data = request.get_json()
    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not current_password or not new_password:
        return jsonify({"error": "Campos incompletos."}), 400

    if not current_user.check_password(current_password):
        return jsonify({"error": "Contraseña actual incorrecta."}), 401

    current_user.set_password(new_password)
    db.session.commit()

    return jsonify({"message": "Contraseña actualizada con éxito."}), 200
