from flask import Blueprint, request, jsonify
from flask_login import login_required, logout_user,current_user, login_user
from extensions import db
from src.database.models import AuthProvider, User
from src.services.integrations.extensions.limiter import limiter
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from extensions import db
import re

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
    
    print("🧪 Usuario buscado:", email)
    print("🧪 Usuario encontrado:", user)
    print("🧪 Proveedor:", user.auth_provider if user else None)
    print(f"🧪 Comparando hash: {user.password_hash} con password ingresado: {password}")

    if not user or user.auth_provider != AuthProvider.LOCAL.value or not user.check_password(password):
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

# ----------------- REGISTER -------------------
@auth_bp.route("/api/v1/auth/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    data = request.get_json()
    email = data.get("email")
    name = data.get("name")
    password = data.get("password")

    # Validar campos
    if not email or not name or not password:
        return jsonify({"error": "Todos los campos son obligatorios"}), 400

    # Validar si ya existe el usuario
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "El email ya está registrado"}), 409

    # Validar contraseña: sin emojis ni caracteres raros
    if contains_emoji(password):
        return jsonify({"error": "La contraseña no debe contener emojis"}), 400

    if len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400

    # Crear usuario
    new_user = User(
        email=email,
        name=name,
        auth_provider=AuthProvider.LOCAL.value,
    )
    new_user.set_password(password)  # encripta contraseña
    db.session.add(new_user)
    db.session.commit()

    # Iniciar sesión automáticamente
    login_user(new_user)

    return jsonify({
        "message": "Usuario registrado con éxito",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name,
            "auth_provider": new_user.auth_provider.value,
            "picture": new_user.picture
        }
    }), 201

# ----------------- FUNCIONES AUXILIARES -------------------
def contains_emoji(text):
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticonos
        u"\U0001F300-\U0001F5FF"  # símbolos y pictogramas
        u"\U0001F680-\U0001F6FF"  # transporte y mapas
        u"\U0001F1E0-\U0001F1FF"  # banderas
        u"\U00002702-\U000027B0"  # signos varios
        u"\U000024C2-\U0001F251"
                           "]+", flags=re.UNICODE)
    return bool(emoji_pattern.search(text))

# ----------------- LOGOUT --------------------
@auth_bp.route("/api/v1/auth/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Sesión cerrada"}), 200

# ---------------- AUTH -ME --------------------
@auth_bp.route("/api/v1/auth/me", methods=["GET"])
@login_required
def get_current_user():
    return jsonify(current_user.to_dict()), 200

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
