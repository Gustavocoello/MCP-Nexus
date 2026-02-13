"""
Archivo - keep_alive_jarvis.py
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

load_dotenv()

TIMEZONE = "America/Guayaquil"
RENDER_SERVER = os.getenv("RENDER_SERVER").lower() == "true"

LOCAL_URL = os.getenv("LOCAL_TARGET3") # Backend de jarvis local
DEPLOY_URL = os.getenv("TARGET_DEPLOYED3") # Backend de jarvis deployado

if RENDER_SERVER:
    TARGET_URL = DEPLOY_URL
else:
    TARGET_URL = LOCAL_URL
    
LOCAL_PING_LOG_URL = os.getenv("LOCAL_PING_LOG_URL") # backend de vite local
DEPLOY_PING_LOG_URL = os.getenv("DEPLOY_PING_LOG_URL") # backend de vite deployado

PING_LOG_URL = DEPLOY_PING_LOG_URL if RENDER_SERVER else LOCAL_PING_LOG_URL

async def ping_target():
    """Envía pings periódicos de MCP → Jarvis y, si es 200, notifica a localhost:8001/ping."""
    while True:
        now = datetime.datetime.now(pytz.timezone(TIMEZONE))
        delay = random.randint(420, 600)  # 7–10 minutos

        try:
            async with aiohttp.ClientSession() as session:
                # Paso 1: Hacer el GET al TARGET_URL
                async with session.get(TARGET_URL, timeout=10) as resp:
                    status = resp.status
                    timestamp = now.strftime('%H:%M:%S')
                    
                    if status == 200:
                        # 🧩 Mensaje unificado
                        log_message = (
                            f"[MCP → Jarvis] 200 Ping a {TARGET_URL} "
                            f"({now.strftime('%H:%M:%S')}) | next_ping={delay}s"
                        )
                        
                        try:
                            async with session.post(
                                PING_LOG_URL,
                                json={"log": log_message},
                                timeout=10,
                                headers={
                                    "Content-Type": "application/json; charset=utf-8"  # Encoding explícito
                                }
                            ) as post_resp:
                                if post_resp.status == 200:
                                    print(f"[MCP → Jarvis] {status} Ping OK | Log enviado ({timestamp}) | next_ping={delay}s")
                                else:
                                    print(f"[MCP → Jarvis] {status} Ping OK | Error al enviar log ({post_resp.status}) {timestamp} | next_ping={delay}s")
                        except Exception as post_e:
                            print(f"[MCP → Jarvis] {status} Ping OK | Falló POST a log: {post_e} | next_ping={delay}s")
                    else:
                        # Ping fallido
                        if status == 429:
                            # Rate limited → esperar más tiempo
                            extra_delay = random.randint(300, 600)  # 5-10 min extra
                            print(f"[MCP → Jarvis] 429 Rate limited ({timestamp}), esperando {extra_delay}s extra")
                            await asyncio.sleep(extra_delay)
                        
                        print(f"[MCP → Jarvis] {status} Ping fallido a {TARGET_URL} ({timestamp}) | next_ping={delay}s")

        except Exception as e:
            print(f"[MCP → Jarvis] Error en ping: {e} ({now.strftime('%H:%M:%S')}) | next_ping={delay}s")

        await asyncio.sleep(delay)


def keep_alive_mcp():
    """Inicia el loop del keep-alive de MCP en segundo plano."""
    def start_loop():
        asyncio.run(ping_target())

    thread = threading.Thread(target=start_loop, daemon=True)
    thread.start()
    print("🚀 Keep-alive MCP iniciado en segundo plano")
