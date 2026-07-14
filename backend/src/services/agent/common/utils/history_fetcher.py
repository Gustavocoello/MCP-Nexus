# src/services/agent/common/history_fetcher.py
import uuid
from datetime import timedelta
from sqlalchemy import text
from sqlalchemy import func, not_
from sqlalchemy.orm import Session

from src.core.time_helper import get_now
from src.database.settings.connection import SessionLocal
from src.database.models.models import Chat, TokenLog, AgentSession, Message

def get_recent_sessions(user_id: str, limit: int = 15, offset: int = 0, time_filter: str = None) -> list[dict]:
    """Fetches the most recent conversational chats and their aggregated token usage."""
    with SessionLocal() as db:
        query = (
            db.query(
                Chat.id,
                Chat.title,
                Chat.summary,
                Chat.updated_at,
                func.sum(TokenLog.total_tokens).label("tokens")
            )
            .outerjoin(TokenLog, TokenLog.chat_id == Chat.id)
            .filter(Chat.user_id == uuid.UUID(str(user_id)))
            .filter(not_(Chat.title.startswith('/'))) # Ignorar chats que son comandos
            .filter(Chat.title != 'Nuevo Chat (CLI)') # Ignorar chats vacíos/huérfanos
        )
        # --- LÓGICA DE FILTRADO POR FECHAS ---
        now = get_now()
        if time_filter == "week":
            query = query.filter(Chat.updated_at >= now - timedelta(days=7))
        elif time_filter == "month":
            query = query.filter(Chat.updated_at >= now - timedelta(days=30))
        elif time_filter == "older":
            query = query.filter(Chat.updated_at < now - timedelta(days=30))

        # --- LÓGICA DE PAGINACIÓN ---
        results = (
            query.group_by(Chat.id)
            .order_by(Chat.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        sessions = []
        for row in results:
            chat_id, title, summary, updated_at, tokens = row
            
            # 1. Título legible (Fallback a summary si title está vacío)
            display_title = title or summary or "Conversación sin título"
            display_title = display_title.split('========')[0].strip()
            if len(display_title) > 45:
                display_title = display_title[:42] + "..."
                
            # 2. Insignia de Tokens consumidos (ej: [🪙 1,450])
            token_str = f" [Tokens: {int(tokens):,}]" if tokens else " [0]"
            
            # 3. Fecha formateada
            date_str = updated_at.strftime("%Y-%m-%d %H:%M") if updated_at else "Reciente"
            
            sessions.append({
                "session_id": str(chat_id), # Mantenemos key "session_id" por compatibilidad con tu CLI
                "summary": f"{display_title}{token_str}",
                "date": date_str
            })
            
        return sessions
    
def delete_chat_permanently(chat_id: str) -> bool:
    """
    Elimina un chat y limpia sus dependencias de forma segura.
    Usa SQL directo (RAW SQL) para evitar los bloqueos y retrasos del ORM de Python.
    """
    try:
        with SessionLocal() as db:
            c_id = str(uuid.UUID(str(chat_id))) # Lo pasamos a string seguro
            
            # 1. Desvincular Tokens (Se conservan para contabilidad)
            db.execute(text("UPDATE tokens SET chat_id = NULL WHERE chat_id = :cid"), {"cid": c_id})
            
            # 2. Borrar Logs HITL
            db.execute(text("DELETE FROM hitl_logs WHERE chat_id = :cid"), {"cid": c_id})
            
            # 3. Borrar Mensajes (La orden directa a la tabla esquiva el error de Foreign Key)
            db.execute(text("DELETE FROM message WHERE chat_id = :cid"), {"cid": c_id})
            
            # 4. Borrar Sesiones de Agentes
            db.execute(text("DELETE FROM agent_sessions WHERE chat_id = :cid"), {"cid": c_id})
            
            # 5. Borrar el Chat principal
            db.execute(text("DELETE FROM chat WHERE id = :cid"), {"cid": c_id})
            
            db.commit()
            return True
            
    except Exception as e:
        # En caso de error extremo, hace rollback automático y lo reporta
        print(f"\n[Error BD]: {e}")
        return False