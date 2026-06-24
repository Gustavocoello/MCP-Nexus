"""
hitl.py — Motor de seguridad de Koda
Incluye: detección por regex, log a DB, control de AgentSession (pause/resume/checkpoint/timeout)
"""

import re
import uuid
import json
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta


from src.core.time_helper import get_now
from src.database.settings.connection import SessionLocal
from src.services.agent.common.utils.session_manager import set_session_waiting
from .security_guard import evaluate_command_security, evaluate_file_security
from src.database.models.models import (
    HITLLog, 
    HITLRiskLevel, 
    HITLVerdict,
    AgentSession, 
    AgentStatus, 
    Chat
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
    status, matched_pattern = evaluate_command_security(text)
    
    if status == "BLOCK":
        return HITLResult(level=HITLRiskLevel.BLOCK, matched=matched_pattern)
    elif status == "CONFIRM":
        return HITLResult(level=HITLRiskLevel.WARN, matched=matched_pattern)
        
    return HITLResult(level=HITLRiskLevel.SAFE)


def validate_path(path: str) -> HITLResult:
    """Validación especial para rutas de archivo (read, list)."""
    is_safe = evaluate_file_security(path)
    if not is_safe:
        return HITLResult(level=HITLRiskLevel.BLOCK, matched="Restricted path or traversal detected")
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
#  FUNCIÓN COMBINADA PARA LAS TOOLS
#  Llama esto desde koda_execute_code, koda_patch_file, etc.
# ─────────────────────────────────────────────────────────────
def get_pending_hitl_requests(user_id: str) -> list[dict]:
    """
    Busca todas las solicitudes HITL en estado PENDING para el usuario.
    Retorna una lista de diccionarios para el CLI.
    """
    with SessionLocal() as db:
        logs = db.query(HITLLog).filter(
            HITLLog.user_id == uuid.UUID(str(user_id)),
            HITLLog.verdict == HITLVerdict.PENDING
        ).all()
        
        return [
            {
                "id": log.id,
                "tool": log.tool_name,
                "input": log.raw_input,
                "matched": log.matched_rule,
                "session_id": str(log.session_id) if log.session_id else None
            }
            for log in logs
        ]

def is_already_approved(session_id: str, tool_name: str, raw_input: str) -> bool:
    """
    Revisa si el usuario ya aprobó esta misma acción en los últimos 5 minutos
    para esta sesión, evitando que el HITL vuelva a bloquearla en el reintento.
    """
    if not session_id:
        return False
        
    from datetime import timedelta
    five_mins_ago = get_now() - timedelta(minutes=5)
    
    with SessionLocal() as db:
        # Buscamos si existe un log aprobado idéntico recientemente
        approved_log = db.query(HITLLog).filter(
            HITLLog.session_id == uuid.UUID(session_id),
            HITLLog.tool_name == tool_name,
            HITLLog.raw_input == raw_input,
            HITLLog.verdict == HITLVerdict.APPROVED,
            HITLLog.created_at >= five_mins_ago
        ).first()
        
        return approved_log is not None

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
    if session_id and is_already_approved(session_id, tool_name, text):
        return None  # Ya fue aprobado, lo dejamos pasar libremente
    
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
       set_session_waiting(session_id)

    return result.block_message() if result.level == HITLRiskLevel.BLOCK else result.warn_message()