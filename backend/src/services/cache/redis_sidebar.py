# ============================================================
# src/cache/redis_sidebar.py
# ============================================================

from typing import List
from sqlalchemy import select
from src.services.cache.redis_client import redis_client
from src.config.logging_config import get_logger
from src.database.models.models import Chat

logger = get_logger('sidebar_cache')

class SidebarCache:
    """Maneja el caché de la lista de chats con fallback a DB"""
    
    CACHE_TTL = 600  # 10 minutos
    
    @staticmethod
    def _get_key(user_id: str) -> str:
        return f"sidebar:chats:{user_id}"
    
    @classmethod
    def get_chats(cls, user_id: str, db_session=None) -> List[dict]:
        """
        Obtiene chats de Redis, con fallback a DB
        SIEMPRE retorna una lista
        """
        key = cls._get_key(user_id)
        
        # 1. INTENTO: Redis
        cached = redis_client.get(key)
        if cached:
            logger.info(f"Sidebar Redis HIT - User {user_id}: {len(cached)} chats")
            return cached
        
        # 2. FALLBACK: Base de datos
        logger.info(f"Sidebar Redis MISS - Fallback a DB para user {user_id}")
        
        if not db_session:
            logger.error("No se proporcionó db_session para fallback")
            return []
        
        try:
            chats = db_session.query(Chat).filter(Chat.user_id == user_id).all()
            
            serialized = [
                {
                    "id": chat.id,
                    "title": chat.title or "Sin título",
                    "created_at": chat.created_at.isoformat(),
                    "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
                    "summary": chat.summary
                }
                for chat in chats
            ]
            
            # Intentar cachear (no crítico si falla)
            redis_client.set(key, serialized, ttl=cls.CACHE_TTL)
            
            logger.info(f"📊 DB Fallback: {len(serialized)} chats para user {user_id}")
            return serialized
        
        except Exception as e:
            logger.error(f"Error en DB fallback: {e}")
            return []
    
    @classmethod
    def set_chats(cls, user_id: str, chats: List) -> bool:
        """Guarda chats en Redis (no crítico si falla)"""
        if not chats:
            return False
        
        serialized = [
            {
                "id": chat.id,
                "title": chat.title or "Sin título",
                "created_at": chat.created_at.isoformat(),
                "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
                "summary": chat.summary
            }
            for chat in chats
        ]
        
        key = cls._get_key(user_id)
        success = redis_client.set(key, serialized, ttl=cls.CACHE_TTL)
        
        if success:
            logger.info(f"💾 Cacheados {len(serialized)} chats para user {user_id}")
        
        return success
    
    @classmethod
    def invalidate_user(cls, user_id: str):
        """Invalida caché del sidebar (no crítico si falla)"""
        key = cls._get_key(user_id)
        redis_client.delete(key)