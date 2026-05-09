import os
import json
from dotenv import load_dotenv
from upstash_redis import Redis

# Cargar credenciales
load_dotenv()
REDIS_URL = os.getenv('REDIS_URL')
REDIS_TOKEN = os.getenv('REDIS_TOKEN')

r = Redis(url=REDIS_URL, token=REDIS_TOKEN)

# Creamos la tarea para la IA
tarea = {
    "id_tarea": "prueba_001",
    "comando": "echo 'console.log(\"¡Hola! El sandbox de 16GB funciona a la perfección. 🚀\");' > app.js && node app.js"
}

# La enviamos a la cola en Upstash
r.lpush('cola_tareas_agente', json.dumps(tarea))
print("¡Tarea enviada a Upstash! Revisa la terminal de tu Worker.")