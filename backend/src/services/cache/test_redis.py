# test_redis.py
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.services.cache.redis_client import redis_client

def test_redis_logic():
    print("--- 🔍 TEST DE INTEGRACIÓN REDIS ---")
    
    # 1. Probar disponibilidad
    available = redis_client.is_available()
    print(f"¿Redis disponible?: {available}")
    
    if not available:
        print("FALLO: El cliente no está disponible. Revisa las credenciales en el .env")
        return

    # 2. Probar escritura (SET)
    test_key = "test:jarvis:001"
    test_data = {"status": "operacional", "message": "Hola desde el test"}
    
    success_set = redis_client.set(test_key, test_data, ttl=60)
    print(f"Escritura exitosa: {success_set}")

    # 3. Probar lectura (GET)
    retrieved_data = redis_client.get(test_key)
    print(f"Datos recuperados: {retrieved_data}")

    if retrieved_data and retrieved_data.get("status") == "operacional":
        print("CONCLUSIÓN: Redis está funcionando perfectamente con tu clase RedisClient.")
    else:
        print("CONCLUSIÓN: Error al recuperar los datos.")

    # 4. Limpieza (DELETE)
    redis_client.delete(test_key)

if __name__ == "__main__":
    test_redis_logic()