# ============================================================
# src/cache/redis_cache.py
# ============================================================

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select
from src.services.cache.redis_client import redis_client
from src.config.logging_config import get_logger
from src.database.models.models import Message
from src.config.time_helper import get_now
from extensions import db

logger = get_logger('chat_cache')

class ChatCache:
    """Maneja el caché de mensajes de chat en Redis con fallback a DB"""
    
    CACHE_TTL = 3600  # 1 hora
    MAX_MESSAGES = 10  # Solo últimos 10 mensajes
    
    @staticmethod
    def _get_key(chat_id: str) -> str:
        return f"chat:messages:{chat_id}"
    
    @classmethod
    def get_messages(cls, chat_id: str, db_session=None) -> List[dict]:
        """
        Obtiene mensajes de Redis, con fallback automático a DB
        
        SIEMPRE retorna una lista (nunca None)
        """
        key = cls._get_key(chat_id)
        
        # 1. INTENTO: Redis
        cached = redis_client.get(key)
        if cached:
            logger.info(f"Redis HIT - Chat {chat_id}: {len(cached)} mensajes")
            return cached
        
        # 2. FALLBACK: Base de datos
        logger.info(f"Redis MISS - Fallback a DB para chat {chat_id}")
        
        if not db_session:
            logger.error("No se proporcionó db_session para fallback")
            return []
        
        try:
            stmt = (
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.created_at.desc())
                .limit(cls.MAX_MESSAGES)
            )
            
            messages = db_session.execute(stmt).scalars().all()
            messages.reverse()  # Orden cronológico
            
            # Serializar
            serialized = [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "html": None,
                    "stable": True
                }
                for msg in messages
            ]
            
            # Intentar cachear para la próxima (no crítico si falla)
            redis_client.set(key, serialized, ttl=cls.CACHE_TTL)
            
            logger.info(f"DB Fallback: {len(serialized)} mensajes para chat {chat_id}")
            return serialized
        
        except Exception as e:
            logger.error(f"Error en DB fallback: {e}")
            return []
    
    @classmethod
    def set_messages(cls, chat_id: str, messages: List) -> bool:
        """
        Guarda mensajes en Redis (solo últimos 10)
        Returns: True si cacheó, False si falló (no crítico)
        """
        if not messages:
            return False
        
        messages_to_cache = messages[-cls.MAX_MESSAGES:]
        
        serialized = [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "html": None,
                "stable": True
            }
            for msg in messages_to_cache
        ]
        
        key = cls._get_key(chat_id)
        success = redis_client.set(key, serialized, ttl=cls.CACHE_TTL)
        
        if success:
            logger.info(f"Cacheados {len(serialized)} mensajes para chat {chat_id}")
        else:
            logger.debug(f"No se pudo cachear chat {chat_id} (no crítico)")
        
        return success
    
    @classmethod
    def invalidate_chat(cls, chat_id: str):
        """Elimina el caché de un chat (no crítico si falla)"""
        key = cls._get_key(chat_id)
        redis_client.delete(key)
    
    @classmethod
    def append_message(cls, chat_id: str, message: dict):
        """
        Agrega un mensaje al caché sin ir a DB
        Si falla, no es crítico (se recargará desde DB)
        """
        key = cls._get_key(chat_id)
        cached = redis_client.get(key)
        
        if not cached:
            return  # No hay caché previo, skip
        
        # Obtenemos la fecha actual en ISO format para consistencia con la DB
        now_iso = get_now().isoformat()
        
        cached.append({
            "id": message.get("id"),
            "role": message.get("role"),
            "content": message.get("content"),
            "created_at": message.get("created_at") or now_iso,
            "html": None,
            "stable": True
        })
        
        # Mantener solo últimos 10
        cached = cached[-cls.MAX_MESSAGES:]
        redis_client.set(key, cached, ttl=cls.CACHE_TTL)