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

# -------- Esperar a que Docker cargue al prender la PC ------------
def esperar_docker():
    print("Verificando si Docker Desktop está corriendo...")
    while True:
        try:
            # Preguntamos a docker si el demonio (engine) está respondiendo
            resultado = subprocess.run(["docker", "info"], capture_output=True, text=True)
            if resultado.returncode == 0:
                print("¡Docker está listo y funcionando!")
                break
        except Exception:
            pass
        print("Docker Desktop aún no está listo. Reintentando en 10 segundos...")
        time.sleep(10)

# Llamamos a la función antes de iniciar el trabajo
esperar_docker()
# -------------------------------------------------------------------

# Conectar a Upstash Redis
try:
    r = Redis(url=REDIS_URL, token=REDIS_TOKEN)
    print("Conectado exitosamente a Upstash Redis en la nube")
except Exception as e:
    print(f"Error conectando a Upstash: {str(e)}")
    exit(1)

# Carpeta local en Windows donde la IA guardará el código
WORKSPACE_LOCAL = os.path.abspath("./work_space")
os.makedirs(WORKSPACE_LOCAL, exist_ok=True)

print("Worker iniciado y esperando tareas...")
print(f"Carpeta de trabajo (Windows): {WORKSPACE_LOCAL}")

# Bucle infinito preguntando a Upstash
while True:
    try:
        tarea_cruda = r.lpop('cola_tareas_agente')
        
        if tarea_cruda:
            if isinstance(tarea_cruda, str):
                tarea = json.loads(tarea_cruda)
            else:
                tarea = tarea_cruda
                
            id_tarea = tarea.get('id_tarea', 'desconocido')
            comando = tarea.get('comando', 'echo "Nada que ejecutar"')
            
            print(f"\nEjecutando tarea [{id_tarea}]: {comando}")
            
            # Comando de Docker para Windows (Corregido el volumen)
            docker_cmd = [
                "docker", "run", "--rm", 
                "--memory=8g", "--cpus=2.0",
                "-v", f"{WORKSPACE_LOCAL}:/workspace", # ESTO ESTABA VACÍO EN TU CÓDIGO
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
            # Si no hay tareas, el script duerme 2 segundos para no saturar
            time.sleep(2)
            
    except Exception as e:
        print(f"Ocurrió un error en el bucle: {str(e)}")
        time.sleep(5)