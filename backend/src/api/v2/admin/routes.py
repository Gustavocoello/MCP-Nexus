import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.logging import get_logger
from src.database.models.models import HITLLog, AgentSession, User
from src.database.settings.connection import get_db

# Importamos tu dependencia de autenticación real
from src.services.auth.auth.auth_middleware import get_current_user

# Importa las funciones de tu hitl.py (Asumo que estas manejan su propia DB interna)
from src.services.agent.Koda.tools.hitl import resolve_hitl_log, resume_session, pause_session

logger = get_logger(__name__)

# Definimos el router con el prefijo
hitl_router = APIRouter(prefix='/admin/hitl', tags=['Admin HITL'])

# ==========================================
# MODELOS PYDANTIC
# ==========================================
class ResolveAction(BaseModel):
    approved: bool
    admin_note: Optional[str] = None

# ==========================================
# UTILIDADES Y DEPENDENCIAS
# ==========================================
def model_to_dict(obj):
    """Convierte un modelo de SQLAlchemy en un diccionario seguro para JSON."""
    if not obj: return None
    data = {}
    for c in obj.__table__.columns:
        val = getattr(obj, c.name)
        if isinstance(val, uuid.UUID): 
            val = str(val)
        elif isinstance(val, datetime): 
            val = val.isoformat()
        elif isinstance(val, Enum): 
            val = val.value
        data[c.name] = val
    return data

def verify_admin(
    user: dict = Depends(get_current_user), 
    db: Session = Depends(get_db)
) -> dict:
    """
    Súper Dependencia: 
    1. Exige un token válido (get_current_user).
    2. Busca al usuario en la BD.
    3. Verifica si es administrador.
    """
    user_db = db.query(User).filter(User.id == user["user_id"]).first()
    
    if not user_db or not user_db.is_admin:
        logger.warning(f"Intento de acceso admin denegado para user_id: {user['user_id']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acceso denegado. Se requieren permisos de administrador."
        )
    return user


# ==========================================
# ENDPOINTS
# ==========================================

@hitl_router.get("/logs")
async def get_hitl_logs(
    admin_user: dict = Depends(verify_admin), # <-- MAGIA: Bloquea si no es admin
    db: Session = Depends(get_db)
):
    try:
        stmt = select(HITLLog).order_by(HITLLog.created_at.desc()).limit(100)
        logs = db.execute(stmt).scalars().all()
        
        return [model_to_dict(log) for log in logs]
        
    except Exception as e:
        logger.exception("Error en /logs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@hitl_router.get("/sessions")
async def get_agent_sessions(
    admin_user: dict = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    try:
        stmt = select(AgentSession).order_by(AgentSession.created_at.desc()).limit(50)
        sessions = db.execute(stmt).scalars().all()
        
        return [model_to_dict(session) for session in sessions]
        
    except Exception as e:
        logger.exception("Error en /sessions")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@hitl_router.post("/logs/{log_id}/resolve")
async def resolve_log(
    log_id: int, 
    action: ResolveAction, # <-- Pydantic valida automáticamente el body
    admin_user: dict = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    try:
        admin_user_id = str(admin_user["user_id"])
        
        # Llamamos a tu función de lógica de negocio
        success = resolve_hitl_log(
            log_id=log_id,
            admin_user_id=admin_user_id,
            approved=action.approved,
            note=action.admin_note
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Log no encontrado o ya resuelto."
            )

        # Si hay sesión asociada, reanudar
        stmt = select(HITLLog).filter_by(id=log_id)
        log = db.execute(stmt).scalar_one_or_none()
        
        if log and log.session_id:
            resume_session(str(log.session_id))
            # TODO: Despertar a LangGraph más adelante

        return {"status": "success", "message": "Log resuelto y sesión reanudada."}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error resolviendo log {log_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@hitl_router.post("/sessions/{session_id}/pause")
async def api_pause_session(
    session_id: uuid.UUID, # <-- FastAPI valida que sea un UUID válido automáticamente
    admin_user: dict = Depends(verify_admin)
):
    try:
        # Llamamos a tu lógica de negocio
        if pause_session(str(session_id)):
            return {"status": "paused"}
            
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No se pudo pausar la sesión."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error pausando sesión {session_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))