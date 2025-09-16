import threading
import requests
import os
import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

RENDER_SERVER = os.getenv("RENDER_SERVER", "FALSE").upper() == "TRUE"
LOCAL_SERVER = os.getenv("LOCAL_SERVER", "FALSE").upper() == "TRUE"

LOCAL_PING_URL = os.getenv("LOCAL_PING_URL")
RENDER_PING_URL = os.getenv("RENDER_PING_URL")

def ping_url(url: str) -> bool:
    """Intenta hacer ping y devuelve True si funciona."""
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            print(f"[KeepAlive] Ping exitoso a {url}")
            return True
        else:
            print(f"[KeepAlive] Ping falló ({r.status_code}) en {url}")
            return False
    except Exception as e:
        print(f"[KeepAlive] Error al hacer ping a {url}: {e}")
        return False

def keep_alive():
    def ping_loop():
        while True:
            now = datetime.datetime.now(pytz.timezone("America/Guayaquil"))
            hour = now.hour

            if 6 <= hour < 24:
                print(f"[KeepAlive] Ejecutando ping loop - {now}")

                success = False

                # Primero intenta local
                if LOCAL_SERVER:
                    success = ping_url(LOCAL_PING_URL)

                # Si local falla, intenta render
                if not success and RENDER_SERVER:
                    success = ping_url(RENDER_PING_URL)

                if not success:
                    print("[KeepAlive] Ningún servidor respondió 😴")

            else:
                print(f"[KeepAlive] En modo sleep (00h-06h GMT-5) - {now}")

            # cada 10 min
            threading.Event().wait(600)

    t = threading.Thread(target=ping_loop, daemon=True)
    t.start()
