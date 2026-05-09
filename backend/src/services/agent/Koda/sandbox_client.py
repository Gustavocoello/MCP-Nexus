import os
import json
import time
import uuid
from upstash_redis import Redis

# Asumimos que el .env de tu backend ya tiene estas variables
REDIS_URL = os.getenv('REDIS_URL')
REDIS_TOKEN = os.getenv('REDIS_TOKEN')

redis_client = Redis(url=REDIS_URL, token=REDIS_TOKEN)

def ejecutar_en_sandbox(comando: str, timeout_segundos: int = 65) -> str:
    """
    Esta es la función (Tool) que el LLM usará.
    Envía un comando al worker de 16GB y espera la respuesta.
    """
    id_tarea = f"tarea_{uuid.uuid4().hex[:8]}"
    
    tarea = {
        "id_tarea": id_tarea,
        "comando": comando
    }
    
    print(f"[Backend] LLM solicitó ejecutar código. ID: {id_tarea}")
    
    # 1. Enviar la tarea a la cola (Upstash)
    redis_client.lpush('cola_tareas_agente', json.dumps(tarea))
    
    # 2. Esperar la respuesta (Polling a la cola de resultados)
    tiempo_inicio = time.time()
    
    while time.time() - tiempo_inicio < timeout_segundos:
        # Extraemos el último resultado
        resultado_crudo = redis_client.lpop('cola_resultados_agente')
        
        if resultado_crudo:
            if isinstance(resultado_crudo, str):
                resultado = json.loads(resultado_crudo)
            else:
                resultado = resultado_crudo
                
            # Verificamos si es la respuesta de nuestra tarea
            if resultado.get("id_tarea") == id_tarea:
                print(f"[Backend] ¡Respuesta recibida del Worker de 16GB!")
                
                # Formatear la respuesta para el LLM
                if resultado.get("exito"):
                    return f"Ejecución exitosa.\nSalida:\n{resultado.get('stdout')}"
                else:
                    return f"Error en la ejecución.\nError:\n{resultado.get('stderr')}\nSalida:\n{resultado.get('stdout')}"
            else:
                # Si por alguna razón es la respuesta de otra tarea, la devolvemos a la cola
                redis_client.rpush('cola_resultados_agente', json.dumps(resultado))
        
        # Esperamos 2 segundos antes de volver a revisar para no saturar Upstash
        time.sleep(2)
        
    return "Timeout: El entorno de ejecución de 16GB no respondió a tiempo o está apagado."