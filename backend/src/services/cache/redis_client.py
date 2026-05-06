# ============================================================
# src/cache/redis_client.py
# ============================================================

import datetime
import os
import redis
import json
from uuid import UUID
from typing import Optional
from dotenv import load_dotenv
from upstash_redis import Redis
from src.config.logging_config import get_logger

logger = get_logger('redis_client')

load_dotenv()

REDIS_URL = os.getenv('REDIS_URL')
REDIS_TOKEN = os.getenv('REDIS_TOKEN')

# Evita el error 'startswith' validando antes de instanciar
if REDIS_URL and REDIS_TOKEN:
    redis_client = Redis(url=REDIS_URL, token=REDIS_TOKEN)
else:
    redis_client = None
    print("ADVERTENCIA: Variables de Redis no encontradas")

class RedisClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.url = os.getenv('REDIS_URL')
        self.token = os.getenv('REDIS_TOKEN')
        self._available = False
        self.client = None

        if not self.url or not self.token:
            logger.warning("Variables REDIS_URL o REDIS_TOKEN ausentes.")
            return

        try:
            # Usamos el SDK de Upstash que es más ligero para tu RAM de 1.5GB
            self.client = Redis(url=self.url, token=self.token)
            # Test simple
            self.client.get("ping") 
            self._available = True
            logger.info("Upstash Redis (HTTP) conectado correctamente")
        except Exception as e:
            logger.warning(f"Redis no disponible: {e}")

    def is_available(self) -> bool:
        return self._available and self.client is not None
    
    def custom_serializer(self, obj):
        """Maneja UUID y Datetime para JSON"""
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    def get(self, key: str) -> Optional[dict]:
        if not self.is_available(): return None
        try:
            value = self.client.get(key)
            if not value: return None
            
            # Si Upstash devuelve un string, lo convertimos a dict
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value # Es un string plano
            return value
        except Exception as e:
            logger.error(f"Error GET {key}: {e}")
            return None

    def set(self, key: str, value: any, ttl: int = 3600) -> bool:
        """
        Guarda valores serializando UUIDs y fechas automáticamente.
        """
        if not self.is_available(): return False
        try:
            # Forzamos la serialización usando nuestro custom_serializer
            # Esto evita el error de "Object of type UUID is not JSON serializable"
            json_value = json.dumps(value, default=self.custom_serializer, ensure_ascii=False)
            
            # Usamos el cliente de Upstash para guardar el string JSON
            self.client.set(key, json_value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Error SET {key}: {e}")
            return False

    def delete(self, key: str):
        if self.is_available():
            self.client.delete(key)
    
    def invalidate_pattern(self, pattern: str) -> bool:
        """Elimina todas las claves que coincidan con un patrón"""
        if not self.is_available():
            return False
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
                logger.info(f"Invalidadas {len(keys)} claves: {pattern}")
            return True
        except Exception as e:
            logger.error(f"Error invalidando {pattern}: {e}")
            return False

# Singleton global
redis_client = RedisClient()