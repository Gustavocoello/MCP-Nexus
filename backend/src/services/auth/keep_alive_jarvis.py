import asyncio
import aiohttp
import random
import datetime
import pytz
import os
import threading
from dotenv import load_dotenv

load_dotenv()

TIMEZONE = "America/Guayaquil"
RENDER_SERVER = os.getenv("RENDER_SERVER").lower() == "true"

LOCAL_URL = os.getenv("LOCAL_TARGET1")
DEPLOY_URL = os.getenv("TARGET_DEPLOYED1")

if RENDER_SERVER:
    TARGET_URL = DEPLOY_URL  # Vite en Render
else:
    TARGET_URL = LOCAL_URL  # Local

async def ping_target():
    """Envía pings periódicos de Jarvis → Vite y también manda el log completo."""
    print("🟢 Iniciando keep-alive Jarvis...")

    while True:
        now = datetime.datetime.now(pytz.timezone(TIMEZONE))
        delay = random.randint(240, 360)  # Próximo ping (4–6 minutos)

        # 🧩 Mensaje unificado
        log_message = (
            f"[Jarvis → Vite] 200 Ping a {TARGET_URL} "
            f"({now.strftime('%H:%M:%S')}) | next_ping={delay}s"
        )

        try:
            # 🔹 Luego enviar el log al backend de Vite
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    TARGET_URL,
                    json={"log": log_message},
                    timeout=5
                ) as resp:
                    if resp.status == 200:
                        print(f" Ping enviado con exito {resp.status}")
                    else:
                        print(f" Error al enviar el ping {resp.status}")

        except Exception as e:
            print(f"[Jarvis → Vite] Error: {e} ({now.strftime('%H:%M:%S')}) | next_ping={delay}s")

        await asyncio.sleep(delay)


def keep_alive():
    """Inicia el loop del keep-alive de Jarvis en segundo plano."""
    def start_loop():
        asyncio.run(ping_target())

    thread = threading.Thread(target=start_loop, daemon=True)
    thread.start()
    print("🚀 Keep-alive Jarvis iniciado en segundo plano (envía logs a Vite por POST)")
