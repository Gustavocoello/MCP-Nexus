# ============================================================
# src/cache/redis_sidebar.py
# ============================================================

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session  # <-- Tipado para FastAPI
from src.services.cache.redis_client import redis_client
from src.core.logging import get_logger
from src.database.models.models import Chat

logger = get_logger('sidebar_cache')

class SidebarCache:
    """Maneja el caché de la lista de chats con fallback a DB"""
    
    CACHE_TTL = 600  # 10 minutos
    
    @staticmethod
    def _get_key(user_id: str, app_id: str) -> str:
        return f"sidebar:chats:{app_id}:{user_id}"
    
    @classmethod
    def get_chats(cls, user_id: str, app_id: str, db_session: Session = None) -> List[dict]:
        """
        Obtiene chats de Redis, con fallback a DB
        SIEMPRE retorna una lista
        """
        key = cls._get_key(user_id, app_id)
        
        # 1. INTENTO: Redis
        cached = redis_client.get(key)
        if cached:
            logger.info(f"[{app_id}] - Sidebar Redis HIT - App {app_id} - User {user_id}")
            return cached
        
        # 2. FALLBACK: Base de datos
        logger.info(f"[{app_id}] - Sidebar Redis MISS - Fallback a DB para app {app_id}")
        
        if not db_session:
            logger.error(f"[{app_id}] - No se proporcionó db_session para fallback")
            return []
        
        try:
            # Sintaxis moderna de SQLAlchemy 2.0
            stmt = (
                select(Chat)
                .where(Chat.user_id == user_id, Chat.app_id == app_id)
                .order_by(Chat.created_at.desc()) # Ordenamos del más nuevo al más viejo
            )
            chats = db_session.execute(stmt).scalars().all()
            
            serialized = [
                {
                    "id": str(chat.id), # Aseguramos que el UUID sea string
                    "title": chat.title or "Sin título",
                    "created_at": chat.created_at.isoformat() if chat.created_at else None,
                    "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
                    "summary": chat.summary
                }
                for chat in chats
            ]
            
            # Intentar cachear (no crítico si falla)
            redis_client.set(key, serialized, ttl=cls.CACHE_TTL)
            
            logger.info(f"[{app_id}] - DB Fallback: {len(serialized)} chats para user {user_id}")
            return serialized
            
        except Exception as e:
            logger.error(f"[{app_id}] - Error en DB fallback: {str(e)}")
            return []
    
    @classmethod
    def set_chats(cls, user_id: str, app_id: str, chats: List) -> bool:
        """Guarda chats en Redis (no crítico si falla)"""
        if not chats:
            return False
        
        serialized = [
            {
                "id": str(chat.id),
                "title": chat.title or "Sin título",
                "created_at": chat.created_at.isoformat() if hasattr(chat, 'created_at') and chat.created_at else None,
                "updated_at": chat.updated_at.isoformat() if hasattr(chat, 'updated_at') and chat.updated_at else None,
                "summary": chat.summary,
                "app_id": app_id
            }
            for chat in chats
        ]
        
        key = cls._get_key(user_id, app_id)
        success = redis_client.set(key, serialized, ttl=cls.CACHE_TTL)
        
        if success:
            logger.info(f"[{app_id}] - Cacheados {len(serialized)} chats para user {user_id}")
            
        return success
    
    @classmethod
    def invalidate_user(cls, user_id: str, app_id: str):
        """Invalida caché del sidebar (no crítico si falla)"""
        key = cls._get_key(user_id, app_id)
        redis_client.delete(key)
        logger.info(f"[{app_id}] - Cache invalidado para user {user_id}")
