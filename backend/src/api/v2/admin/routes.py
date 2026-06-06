import uuid
from datetime import datetime
from enum import Enum
from flask import Blueprint, jsonify, request, g
from pydantic import BaseModel, ValidationError
from sqlalchemy import select

from src.core.logging import get_logger
from src.database.models.models import HITLLog, AgentSession, User # Asegúrate de importar User
from src.database.settings.connection import SessionLocal

# Importa tu decorador de autenticación (ajusta la ruta según tu proyecto)
from src.services.auth.auth.auth_middleware import auth_required 

# Importa las funciones de tu hitl.py
from src.services.agent.Koda.tools.hitl import resolve_hitl_log, resume_session, pause_session

logging = get_logger(__name__)
hitl_bp = Blueprint('admin_hitl', __name__, url_prefix='/admin/hitl')

class ResolveAction(BaseModel):
    approved: bool
    admin_note: str | None = None

def model_to_dict(obj):
    """Convierte un modelo de SQLAlchemy en un diccionario seguro para JSON."""
    if not obj: return None
    data = {}
    for c in obj.__table__.columns:
        val = getattr(obj, c.name)
        if isinstance(val, uuid.UUID): val = str(val)
        elif isinstance(val, datetime): val = val.isoformat()
        elif isinstance(val, Enum): val = val.value
        data[c.name] = val
    return data

def verify_is_admin(db_session, user_id):
    """Helper para verificar si el usuario es admin."""
    stmt = select(User).filter_by(id=user_id)
    user = db_session.execute(stmt).scalar_one_or_none()
    return user and user.is_admin

# ─────────────────────────────────────────────────────────────
#  ENDPOINTS FLASK (100% Operativos)
# ─────────────────────────────────────────────────────────────

@hitl_bp.route("/logs", methods=["GET"])
@auth_required
def get_hitl_logs():
    db_session = SessionLocal()
    try:
        if not verify_is_admin(db_session, g.user_id):
            return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

        stmt = select(HITLLog).order_by(HITLLog.created_at.desc()).limit(100)
        logs = db_session.execute(stmt).scalars().all()
        return jsonify([model_to_dict(log) for log in logs]), 200
    except Exception as e:
        logging.error(f"Error en /logs: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@hitl_bp.route("/sessions", methods=["GET"])
@auth_required
def get_agent_sessions():
    db_session = SessionLocal()
    try:
        if not verify_is_admin(db_session, g.user_id):
            return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

        stmt = select(AgentSession).order_by(AgentSession.created_at.desc()).limit(50)
        sessions = db_session.execute(stmt).scalars().all()
        return jsonify([model_to_dict(session) for session in sessions]), 200
    except Exception as e:
        logging.error(f"Error en /sessions: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@hitl_bp.route("/logs/<int:log_id>/resolve", methods=["POST"])
@auth_required
def resolve_log(log_id):
    db_session = SessionLocal()
    try:
        # Validación Admin
        if not verify_is_admin(db_session, g.user_id):
            return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

        # Validación Payload
        data = request.get_json()
        if not data:
            return jsonify({"detail": "Falta el cuerpo de la petición"}), 400
        
        try:
            action = ResolveAction(**data)
        except ValidationError as e:
            return jsonify({"detail": "Datos inválidos", "errors": e.errors()}), 422

        # Resolviendo usando g.user_id
        admin_user_id = str(g.user_id)
        success = resolve_hitl_log(
            log_id=log_id,
            admin_user_id=admin_user_id,
            approved=action.approved,
            note=action.admin_note
        )
        
        if not success:
            return jsonify({"detail": "Log no encontrado o ya resuelto."}), 400

        # Si hay sesión asociada, reanudar
        stmt = select(HITLLog).filter_by(id=log_id)
        log = db_session.execute(stmt).scalar_one_or_none()
        
        if log and log.session_id:
            resume_session(str(log.session_id))
            # TODO: Despertar a LangGraph más adelante

        return jsonify({"status": "success", "message": "Log resuelto y sesión reanudada."}), 200

    except Exception as e:
        db_session.rollback()
        logging.error(f"Error resolviendo log {log_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@hitl_bp.route("/sessions/<uuid:session_id>/pause", methods=["POST"])
@auth_required
def api_pause_session(session_id):
    db_session = SessionLocal()
    try:
        if not verify_is_admin(db_session, g.user_id):
            return jsonify({"error": "Acceso denegado. Se requieren permisos de administrador."}), 403

        if pause_session(str(session_id)):
            return jsonify({"status": "paused"}), 200
            
        return jsonify({"detail": "No se pudo pausar la sesión."}), 400
    except Exception as e:
        logging.error(f"Error pausando sesión {session_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()