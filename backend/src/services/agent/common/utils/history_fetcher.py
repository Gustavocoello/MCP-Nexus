# src/services/agent/common/history_fetcher.py
import uuid
from sqlalchemy import func
from sqlalchemy.orm import Session
from src.database.settings.connection import SessionLocal

# Importamos Chat y TokenLog en lugar de AgentSession
from src.database.models.models import Chat, TokenLog

def get_recent_sessions(user_id: str, limit: int = 15) -> list[dict]:
    """Fetches the most recent conversational chats and their aggregated token usage."""
    with SessionLocal() as db:
        # Hacemos un JOIN entre Chat y TokenLog para sumar los tokens
        results = (
            db.query(
                Chat.id,
                Chat.title,
                Chat.summary,
                Chat.updated_at,
                func.sum(TokenLog.total_tokens).label("tokens")
            )
            .outerjoin(TokenLog, TokenLog.chat_id == Chat.id)
            .filter(Chat.user_id == uuid.UUID(str(user_id)))
            .group_by(Chat.id)
            .order_by(Chat.updated_at.desc())
            .limit(limit)
            .all()
        )
        
        sessions = []
        for row in results:
            chat_id, title, summary, updated_at, tokens = row
            
            # 1. Título legible (Fallback a summary si title está vacío)
            display_title = title or summary or "Conversación sin título"
            if len(display_title) > 45:
                display_title = display_title[:42] + "..."
                
            # 2. Insignia de Tokens consumidos (ej: [🪙 1,450])
            token_str = f" [🪙 {int(tokens):,}]" if tokens else " [🪙 0]"
            
            # 3. Fecha formateada
            date_str = updated_at.strftime("%Y-%m-%d %H:%M") if updated_at else "Reciente"
            
            sessions.append({
                "session_id": str(chat_id), # Usamos el ID del Chat
                "summary": f"{display_title}{token_str}",
                "date": date_str
            })
            
        return sessions