"""
hitl.py — Motor de seguridad de Koda
Incluye: detección por regex, log a DB, control de AgentSession (pause/resume/checkpoint/timeout)
"""

import re
import uuid
import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from src.database.settings.connection import SessionLocal
from src.core.time_helper import get_now

# Importa los modelos nuevos
from src.database.models.models import (
    HITLLog, HITLRiskLevel, HITLVerdict,
    AgentSession, AgentStatus,
)


# ─────────────────────────────────────────────────────────────
#  REGLAS  (fácil de extender — solo agrega patrones aquí)
# ─────────────────────────────────────────────────────────────

RULES: dict[HITLRiskLevel, list[str]] = {
    HITLRiskLevel.BLOCK: [
        # Filesystem destructivo
        r"rm\s+-[rf]{1,2}",
        r"shutil\.rmtree",
        r"os\.remove\s*\(",
        r"pathlib.*\.unlink\s*\(",
        r"chmod\s+[0-7]*7[0-7]*",
        # Ejecución arbitraria
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"subprocess.*shell\s*=\s*True",
        r"os\.system\s*\(",
        # Path traversal
        r"\.\.[/\\]",
        # Git destructivo inmediato
        r"git\s+push\s+(--force|-f)\b",
        # Sistema
        r"\b(reboot|shutdown|halt|poweroff)\b",
        r"mkfs\b",
        r"dd\s+if=",
    ],
    HITLRiskLevel.WARN: [
        # Base de datos
        r"DROP\s+TABLE",
        r"DROP\s+DATABASE",
        r"TRUNCATE\s+TABLE",
        r"TRUNCATE\b",
        r"DELETE\s+FROM\s+\w+\s*(?!WHERE)",   # DELETE sin WHERE
        # Git reversible pero peligroso
        r"git\s+reset\s+--hard",
        r"git\s+clean\s+-[fdx]",
        r"git\s+push\b",                       # push normal → solo warn
    ],
}


# ─────────────────────────────────────────────────────────────
#  RESULTADO DEL CHEQUEO
# ─────────────────────────────────────────────────────────────

@dataclass
class HITLResult:
    level:   HITLRiskLevel
    matched: Optional[str] = None

    @property
    def is_safe(self) -> bool:
        return self.level == HITLRiskLevel.SAFE

    def block_message(self) -> str:
        return (
            f"HITL_BLOCKED: Patrón peligroso detectado → `{self.matched}`.\n"
            "Esta operación está bloqueada permanentemente. "
            "Busca una alternativa más segura y NO reintentes este comando."
        )

    def warn_message(self) -> str:
        return (
            f"HITL_REQUIRES_APPROVAL: Operación de riesgo detectada → `{self.matched}`.\n"
            "Detente completamente. Explica al usuario qué hará este comando "
            "y espera que el admin responda 'confirmo' desde el panel antes de continuar."
        )


# ─────────────────────────────────────────────────────────────
#  MOTOR DE DETECCIÓN
# ─────────────────────────────────────────────────────────────

def hitl_check(text: str) -> HITLResult:
    """Evalúa BLOCK primero, luego WARN. Retorna HITLResult."""
    for level in (HITLRiskLevel.BLOCK, HITLRiskLevel.WARN):
        for pattern in RULES[level]:
            if re.search(pattern, text, re.IGNORECASE):
                return HITLResult(level=level, matched=pattern)
    return HITLResult(level=HITLRiskLevel.SAFE)


def validate_path(path: str) -> HITLResult:
    """Validación especial para rutas de archivo (read, list)."""
    if re.search(r"\.\.[/\\]", path):
        return HITLResult(level=HITLRiskLevel.BLOCK, matched="path traversal")
    return HITLResult(level=HITLRiskLevel.SAFE)


# ─────────────────────────────────────────────────────────────
#  LOG A BASE DE DATOS
# ─────────────────────────────────────────────────────────────

def log_hitl_event(
    user_id: str,
    tool_name: str,
    raw_input: str,
    result: HITLResult,
    chat_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> int:
    """
    Persiste el evento HITL en la DB.
    Retorna el ID del registro creado.
    """
    # Determina verdict inicial según nivel
    if result.level == HITLRiskLevel.BLOCK:
        verdict = HITLVerdict.BLOCKED
    elif result.level == HITLRiskLevel.WARN:
        verdict = HITLVerdict.PENDING   # Espera acción del admin
    else:
        return -1   # SAFE → no loguear

    with SessionLocal() as db:
        log = HITLLog(
            user_id      = uuid.UUID(str(user_id)),
            chat_id      = uuid.UUID(str(chat_id))    if chat_id    else None,
            session_id   = uuid.UUID(str(session_id)) if session_id else None,
            tool_name    = tool_name,
            raw_input    = raw_input[:4000],   # truncar si es muy largo
            matched_rule = result.matched,
            risk_level   = result.level,
            verdict      = verdict,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log.id


def resolve_hitl_log(
    log_id: int,
    admin_user_id: str,
    approved: bool,
    note: Optional[str] = None,
) -> bool:
    """
    El admin aprueba o rechaza un evento WARN pendiente.
    Retorna True si se resolvió correctamente.
    """
    with SessionLocal() as db:
        log = db.query(HITLLog).filter(HITLLog.id == log_id).first()
        if not log or log.verdict != HITLVerdict.PENDING:
            return False

        log.verdict     = HITLVerdict.APPROVED if approved else HITLVerdict.REJECTED
        log.resolved_by = uuid.UUID(str(admin_user_id))
        log.resolved_at = get_now()
        log.admin_note  = note
        db.commit()
        return True


# ─────────────────────────────────────────────────────────────
#  CONTROL DE SESIÓN LARGA (pause / resume / checkpoint / timeout)
# ─────────────────────────────────────────────────────────────

def create_agent_session(
    user_id: str,
    task_description: str,
    chat_id: Optional[str] = None,
    steps_total: Optional[int] = None,
    timeout_seconds: int = 3600,
) -> str:
    """Crea una nueva AgentSession. Retorna el session_id (UUID str)."""
    session_id = uuid.uuid4()
    with SessionLocal() as db:
        session = AgentSession(
            id               = session_id,
            user_id          = uuid.UUID(str(user_id)),
            chat_id          = uuid.UUID(str(chat_id)) if chat_id else None,
            task_description = task_description,
            steps_total      = steps_total,
            timeout_seconds  = timeout_seconds,
            status           = AgentStatus.RUNNING,
        )
        db.add(session)
        db.commit()
    return str(session_id)


def update_session_step(session_id: str, current_step: str, steps_completed: int) -> None:
    """Actualiza el paso actual y el heartbeat. Llama esto en cada iteración del agente."""
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session:
            return
        session.current_step    = current_step
        session.steps_completed = steps_completed
        session.last_heartbeat  = get_now()
        db.commit()


def save_checkpoint(session_id: str, checkpoint_data: dict) -> None:
    """Serializa y guarda el estado del agente para poder resumirlo después."""
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session:
            return
        session.checkpoint_data = json.dumps(checkpoint_data, ensure_ascii=False)
        session.last_heartbeat  = get_now()
        db.commit()


def load_checkpoint(session_id: str) -> Optional[dict]:
    """Carga el último checkpoint guardado. Retorna None si no existe."""
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session or not session.checkpoint_data:
            return None
        return json.loads(session.checkpoint_data)


def pause_session(session_id: str) -> bool:
    """Pausa la sesión. El agente debe verificar is_paused() en su loop."""
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session or session.status != AgentStatus.RUNNING:
            return False
        session.status    = AgentStatus.PAUSED
        session.paused_at = get_now()
        db.commit()
        return True


def resume_session(session_id: str) -> bool:
    """Reanuda una sesión pausada o en espera de aprobación HITL."""
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session or session.status not in (AgentStatus.PAUSED, AgentStatus.WAITING):
            return False
        session.status         = AgentStatus.RUNNING
        session.last_heartbeat = get_now()
        db.commit()
        return True


def complete_session(session_id: str, result_summary: str) -> None:
    """Marca la sesión como completada."""
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session:
            return
        session.status         = AgentStatus.COMPLETED
        session.result_summary = result_summary
        session.completed_at   = get_now()
        db.commit()


def fail_session(session_id: str, error_message: str) -> None:
    """Marca la sesión como fallida."""
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session:
            return
        session.status        = AgentStatus.FAILED
        session.error_message = error_message
        session.completed_at  = get_now()
        db.commit()


def is_paused(session_id: str) -> bool:
    """
    El agente llama esto en cada iteración de su loop.
    Si está PAUSED o WAITING, debe detenerse y esperar.
    """
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session:
            return False
        return session.status in (AgentStatus.PAUSED, AgentStatus.WAITING)


def check_timeout(session_id: str) -> bool:
    """
    Verifica si la sesión superó su timeout por inactividad (sin heartbeat).
    Si sí, la marca como TIMEOUT y retorna True.
    """
    with SessionLocal() as db:
        session = db.query(AgentSession).filter(AgentSession.id == uuid.UUID(session_id)).first()
        if not session or session.status not in (AgentStatus.RUNNING, AgentStatus.WAITING):
            return False

        elapsed = (get_now() - session.last_heartbeat).total_seconds()
        if elapsed > session.timeout_seconds:
            session.status       = AgentStatus.TIMEOUT
            session.error_message = f"Sin actividad por {int(elapsed)}s (límite: {session.timeout_seconds}s)"
            session.completed_at = get_now()
            db.commit()
            return True
        return False


# ─────────────────────────────────────────────────────────────
#  FUNCIÓN COMBINADA PARA LAS TOOLS
#  Llama esto desde koda_execute_code, koda_patch_file, etc.
# ─────────────────────────────────────────────────────────────

def hitl_guard(
    text: str,
    tool_name: str,
    user_id: str,
    chat_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Optional[str]:
    """
    Punto de entrada único para las tools de Koda.

    Uso:
        block_msg = hitl_guard(command, "koda_execute_code", user_id, chat_id, session_id)
        if block_msg:
            return block_msg   # devuelve el mensaje al LLM y detiene la ejecución

    Retorna:
        - str  con el mensaje de bloqueo/advertencia si se interceptó
        - None si es SAFE (la tool puede continuar)
    """
    result = hitl_check(text)

    if result.is_safe:
        return None

    # Loguear a DB
    log_id = log_hitl_event(
        user_id    = user_id,
        tool_name  = tool_name,
        raw_input  = text,
        result     = result,
        chat_id    = chat_id,
        session_id = session_id,
    )

    # Si es WARN, marcar la sesión como WAITING
    if result.level == HITLRiskLevel.WARN and session_id:
        with SessionLocal() as db:
            session = db.query(AgentSession).filter(
                AgentSession.id == uuid.UUID(session_id)
            ).first()
            if session:
                session.status = AgentStatus.WAITING
                db.commit()

    return result.block_message() if result.level == HITLRiskLevel.BLOCK else result.warn_message()