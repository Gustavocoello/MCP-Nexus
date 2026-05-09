"""
Archivo - keep_alive_jarvis.py
"""

import asyncio
from http import client
import aiohttp
import random
import os
import threading
from dotenv import load_dotenv
from src.config.time_helper import get_now
from src.database.config.connection import SessionLocal
from src.database.models.models import PingLog

load_dotenv()

RENDER_SERVER = os.getenv("RENDER_SERVER").lower() == "true"

LOCAL_URL = os.getenv("LOCAL_PING") # Contabilidad 
DEPLOY_URL = os.getenv("PRODU_PING")

if RENDER_SERVER:
    TARGET_URL = DEPLOY_URL  # Vite en Render
else:
    TARGET_URL = LOCAL_URL  # Local

async def ping_target():
    """Hace GET al target y guarda el resultado (200, 404, 500, etc.) en la DB local."""
    print(f"🟢 Monitor iniciado: Apuntando a {TARGET_URL}")
    
    while True:
        now = get_now()
        delay = random.randint(420, 600)
        status_code = 0
        log_message = ""
        client_host = "localhost"  

        # 1. Intentar la petición GET
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(TARGET_URL, timeout=15) as resp:
                    status_code = resp.status
                    log_message = f"{status_code} Ping OK: {TARGET_URL}"
        except Exception as e:
            status_code = 500  # Error de conexión
            log_message = f"500 Error: Host Down ({TARGET_URL})"
        # 2. GUARDAR DIRECTO EN BASE DE DATOS
        # Abrimos sesión justo antes de usarla
        db = SessionLocal()
        try:
            new_log = PingLog(
                service="vite-contabilidad",
                event_type="self_monitor",
                message=log_message,
                status_code=status_code,
                client_ip=client_host,
                next_ping_sc=delay,
                timestamp=now  # Usando el nombre correcto 'timestamp' que vimos antes
            )
            db.add(new_log)
            db.commit()
            print(f"Ping Log guardado en DB: {status_code} | {now.strftime('%H:%M:%S')}")
        except Exception as db_e:
            db.rollback()
            print(f"Error al escribir en DB: {db_e}")
        finally:
            db.close()

        # 3. Esperar al siguiente ciclo
        await asyncio.sleep(delay)

def keep_alive():
    """Inicia el monitor en segundo plano."""
    def start_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ping_target())

    thread = threading.Thread(target=start_loop, daemon=True)
    thread.start()
    print("🚀 Keep-alive local (DB Direct) ejecutándose.")