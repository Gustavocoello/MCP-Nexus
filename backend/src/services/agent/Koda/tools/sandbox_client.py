import os
import json
import time
import uuid
from upstash_redis import Redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv('REDIS_URL')
REDIS_TOKEN = os.getenv('REDIS_TOKEN')

# Manejo de error por si faltan credenciales en testing local
if REDIS_URL and REDIS_TOKEN:
    redis_client = Redis(url=REDIS_URL, token=REDIS_TOKEN)
else:
    redis_client = None

def execute_in_sandbox(command: str, timeout_seconds: int = 65) -> str:
    """
    Envía un comando al worker de 8GB y espera la respuesta.
    (Mantiene las llaves del JSON en español para compatibilidad con el Worker existente).
    """
    if not redis_client:
        return "Error: Upstash Redis not configured. Sandbox offline."

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    # Mantenemos las keys en español porque el Worker las espera así
    task_payload = {
        "id_tarea": task_id,
        "comando": command
    }
    
    print(f"\n[KODA SANDBOX] Executing: {command[:50]}... ID: {task_id}")
    
    # Enviar a la cola (Nombre de cola original)
    redis_client.lpush('cola_tareas_agente', json.dumps(task_payload))
    
    # Polling de resultados
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        raw_result = redis_client.lpop('cola_resultados_agente')
        
        if raw_result:
            result = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
                
            if result.get("id_tarea") == task_id:
                print(f"[KODA SANDBOX] Response received!")
                
                if result.get("exito"):
                    # Extraer stdout de forma segura
                    stdout = result.get('stdout', '')
                    if stdout is None: stdout = ''
                    
                    # SI EL COMANDO FUNCIONÓ PERO NO DEVOLVIÓ NADA
                    if not stdout.strip():
                        return "Execution successful. No output produced in console (empty output)."
                        
                    return f"Execution successful.\nOutput (stdout):\n{stdout}"
            else:
                # Si el resultado es de otra tarea, lo devolvemos a la cola
                redis_client.rpush('cola_resultados_agente', json.dumps(result))
        
        time.sleep(2)
        
    return "Timeout: The 8GB execution environment did not respond in time."