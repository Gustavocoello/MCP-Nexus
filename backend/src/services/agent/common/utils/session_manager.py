# from src/services/agent/common/utils
"""
session_manager.py — Control de estado de las sesiones de Agentes.
Maneja pausas, resúmenes, checkpoints y timeouts.
"""
import re
import uuid
import json
from typing import Optional
from sqlalchemy.orm import Session

from src.database.settings.connection import SessionLocal
from src.core.time_helper import get_now
from src.database.models.models import AgentSession, AgentStatus, Chat

def create_agent_session(
    user_id: str,
    task_description: str,
    chat_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    assigned_agent: str = "jarvis",
    steps_total: Optional[int] = None,
    timeout_seconds: int = 3600,
) -> str:
    """Crea una nueva AgentSession. Retorna el session_id (UUID str)."""
    session_id = uuid.uuid4()
    with SessionLocal() as db:
        parsed_user_id = uuid.UUID(str(user_id))
        if chat_id:
            parsed_chat_id = uuid.UUID(str(chat_id))
            existing_chat = db.query(Chat).filter(Chat.id == parsed_chat_id).first()
            if not existing_chat:
                clean_desc = task_description.replace('\n', ' ').strip() if task_description else "Sesión de Koda"
                
                # --- NUEVO: Borramos la etiqueta de sistema del título ---
                clean_desc = re.sub(r'\[SYSTEM:.*?\]', '', clean_desc, flags=re.DOTALL).strip()
                # Evitamos que un comando se vuelva un chat
                if clean_desc.startswith('/'):
                    clean_desc = "Comando de Sistema"
                if not clean_desc: 
                    clean_desc = "Sesión de Agente"
                # ---------------------------------------------------------
                
                short_title = (clean_desc[:45] + "...") if len(clean_desc) > 45 else clean_desc
                new_chat = Chat(
                    id=parsed_chat_id,
                    user_id= parsed_user_id,
                    title=short_title,
                    summary=clean_desc
                )
                db.add(new_chat)
                db.commit()
        else:
            parsed_chat_id = None
                
        session = AgentSession(
            id               = session_id,
            user_id          = parsed_user_id,
            chat_id          = parsed_chat_id,
            thread_id        = thread_id,
            assigned_agent   = assigned_agent,
            task_description = task_description,
            steps_total      = steps_total,
            timeout_seconds  = timeout_seconds,
            status           = AgentStatus.RUNNING,
        )
        db.add(session)
        db.commit()
    return str(session_id)

def update_session_step(session_id: str, current_step: str, steps_completed: int) -> None:
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session: return
        session.current_step    = current_step
        session.steps_completed = steps_completed
        session.last_heartbeat  = get_now()
        db.commit()

def save_checkpoint(session_id: str, checkpoint_data: dict) -> None:
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session: return
        session.checkpoint_data = json.dumps(checkpoint_data, ensure_ascii=False)
        session.last_heartbeat  = get_now()
        db.commit()

def load_checkpoint(session_id: str) -> Optional[dict]:
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session or not session.checkpoint_data: return None
        return json.loads(session.checkpoint_data)

def pause_session(session_id: str) -> bool:
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session or session.status != AgentStatus.RUNNING: return False
        session.status    = AgentStatus.PAUSED
        session.paused_at = get_now()
        db.commit()
        return True

def resume_session(session_id: str) -> bool:
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session or session.status not in (AgentStatus.PAUSED, AgentStatus.WAITING): return False
        session.status         = AgentStatus.RUNNING
        session.last_heartbeat = get_now()
        db.commit()
        return True

def complete_session(session_id: str, result_summary: str) -> None:
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session: return
        session.status         = AgentStatus.COMPLETED
        session.result_summary = result_summary
        session.completed_at   = get_now()
        db.commit()

def fail_session(session_id: str, error_message: str) -> None:
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session: return
        session.status        = AgentStatus.FAILED
        session.error_message = error_message
        session.completed_at  = get_now()
        db.commit()

def is_paused(session_id: str) -> bool:
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session: return False
        return session.status in (AgentStatus.PAUSED, AgentStatus.WAITING)

def check_timeout(session_id: str) -> bool:
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session or session.status not in (AgentStatus.RUNNING, AgentStatus.WAITING): return False
        elapsed = (get_now() - session.last_heartbeat).total_seconds()
        if elapsed > session.timeout_seconds:
            session.status        = AgentStatus.TIMEOUT
            session.error_message = f"Sin actividad por {int(elapsed)}s (límite: {session.timeout_seconds}s)"
            session.completed_at  = get_now()
            db.commit()
            return True
        return False

def set_session_waiting(session_id: str) -> None:
    """Coloca la sesión en WAITING (Usado por HITL cuando intercepta un WARN)."""
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if session:
            session.status = AgentStatus.WAITING
            db.commit()