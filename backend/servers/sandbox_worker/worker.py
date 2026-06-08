import subprocess
import json
import os
import time
from dotenv import load_dotenv
from upstash_redis import Redis

# Cargar variables de entorno
load_dotenv()

UBUNTU = os.getenv('LINUX_HOST')
REDIS_URL = os.getenv('REDIS_URL')
REDIS_TOKEN = os.getenv('REDIS_TOKEN')

# Conectar a Upstash Redis
try:
    r = Redis(url=REDIS_URL, token=REDIS_TOKEN)
    print("Conectado exitosamente a Upstash Redis en la nube")
except Exception as e:
    print(f"Error conectando a Upstash: {e}")
    exit(1)

# Carpeta local en Windows donde la IA guardará el código
WORKSPACE_LOCAL = os.path.abspath("./espacio_trabajo")
os.makedirs(WORKSPACE_LOCAL, exist_ok=True)

print("Worker de 16GB iniciado y esperando tareas...")
print(f"Carpeta de trabajo (Windows): {WORKSPACE_LOCAL}")

# Bucle infinito preguntando a Upstash
while True:
    try:
        # Usamos lpop (saca el primer elemento de la lista). Si no hay, devuelve None.
        tarea_cruda = r.lpop('cola_tareas_agente')
        
        if tarea_cruda:
            # Upstash a veces auto-convierte el JSON a diccionario. Lo validamos:
            if isinstance(tarea_cruda, str):
                tarea = json.loads(tarea_cruda)
            else:
                tarea = tarea_cruda
                
            id_tarea = tarea.get('id_tarea', 'desconocido')
            comando = tarea.get('comando', 'echo "Nada que ejecutar"')
            
            print(f"\n Ejecutando tarea [{id_tarea}]: {comando}")
            
            # Comando de Docker para Windows
            docker_cmd = [
                "docker", "run", "--rm", 
                "--memory=8g", "--cpus=2.0",
                "-v", f"{WORKSPACE_LOCAL}:/workspace",
                "sandbox-ia", 
                "bash", "-c", comando
            ]
            
            # Ejecutar de forma segura
            resultado = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=60 # Límite de 1 minuto
            )
            
            respuesta = {
                "id_tarea": id_tarea,
                "exito": resultado.returncode == 0,
                "stdout": resultado.stdout,
                "stderr": resultado.stderr
            }
            
            # Enviar resultado de vuelta a Upstash
            r.lpush('cola_resultados_agente', json.dumps(respuesta))
            print(f"Tarea [{id_tarea}] completada. Resultados en la nube.")
            
        else:
            # Si no hay tareas, el script duerme 2 segundos para no saturar la API de Upstash
            time.sleep(2)
            
    except Exception as e:
        print(f"Ocurrió un error en el bucle: {e}")
        time.sleep(5) # Si hay un error de red, espera 5 segs antes de reintentar