"""
Archivo - keep_alive.py
"""

import asyncio
import aiohttp
import random
import datetime
from isodate import LOCAL
import pytz
import os
import threading
from dotenv import load_dotenv
from .time_helper import get_now

load_dotenv()

RENDER_SERVER = os.getenv("RENDER_SERVER").lower() == "true"

LOCAL_URL = os.getenv("LOCAL_PING") # Backend de jarvis local
DEPLOY_URL = os.getenv("PRODU_PING") # Backend de jarvis deployado

if RENDER_SERVER:
    TARGET_URL = DEPLOY_URL
else:
    TARGET_URL = LOCAL_URL
    
LOCAL_PING_LOG_URL = os.getenv("LOCAL_PING_LOG_URL") # backend de vite local
DEPLOY_PING_LOG_URL = os.getenv("DEPLOY_PING_LOG_URL") # backend de vite deployado

PING_LOG_URL = DEPLOY_PING_LOG_URL if RENDER_SERVER else LOCAL_PING_LOG_URL

async def ping_target():
    """Envía pings periódicos y reporta CUALQUIER resultado al backend central."""
    while True:
        now = get_now()
        delay = random.randint(420, 600)
        timestamp = now.strftime('%H:%M:%S')
        log_message = ""
        status_code = 0

        async with aiohttp.ClientSession() as session:
            try:
                # 1. Intentar el PING (GET)
                async with session.get(TARGET_URL, timeout=10) as resp:
                    status_code = resp.status
                    if status_code in [200, 201]:
                        log_message = f"200 OK en {TARGET_URL}|next_ping={delay}s"
                    else:
                        log_message = f"{status_code} Error de conection a {TARGET_URL}|next_ping={delay}s"
            
            except Exception as e:
                # Si el servidor destino está APAGADO (Error de conexión)
                status_code = 503 # Servicio no disponible
                log_message = f"{status_code} Error: Host down {TARGET_URL}|next_ping={delay}s"

            # 2. ENVIAR EL LOG (POST) - Siempre se ejecuta, pase lo que pase arriba
            print(log_message) # Print en la consola local
            
            try:
                async with session.post(
                    PING_LOG_URL,
                    json={"log": log_message},
                    timeout=10,
                    headers={"Content-Type": "application/json; charset=utf-8"}
                ) as post_resp:
                    # Aceptamos 200 y 201 como éxito
                    if post_resp.status in [200, 201]:
                        print(f"Log reportado al Backend ({post_resp.status})")
                    else:
                        print(f"Backend recibió log pero respondió {post_resp.status}")
            except Exception as post_e:
                print(f"Error fatal: Ni siquiera se pudo reportar al Backend: {post_e}")

        # 3. Manejo de Rate Limit antes de dormir
        if status_code == 429:
            await asyncio.sleep(300) # Espera 5 min extra si hay baneo temporal

        await asyncio.sleep(delay)


def keep_alive_mcp():
    """Inicia el loop del keep-alive de MCP en segundo plano."""
    def start_loop():
        asyncio.run(ping_target())

    thread = threading.Thread(target=start_loop, daemon=True)
    thread.start()
    print("🚀 Keep-alive MCP iniciado en segundo plano")
