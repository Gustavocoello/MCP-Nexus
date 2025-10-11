import threading
import requests
import os
from dotenv import load_dotenv

load_dotenv()

RENDER_SERVER = os.getenv("RENDER_SERVER").upper() == "TRUE"

RENDER_PING_URL = os.getenv("TARGET_PING_URL")
RENDER_PING_URL2 = os.getenv("TARGET_PING_URL2")


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
        toggle = True  # alternador entre URL1 y URL2
        if RENDER_SERVER:
            if toggle:
                    if RENDER_PING_URL:
                        ping_url(RENDER_PING_URL)
            else:
                    if RENDER_PING_URL2:
                        ping_url(RENDER_PING_URL2)

            # alternar entre primer y segundo render
            toggle = not toggle

        else:
                print(f"[KeepAlive] En modo sleep (00h-06h GMT-5) - {now}")

        # cada 5 min
        threading.Event().wait(300)

    t = threading.Thread(target=ping_loop, daemon=True)
    t.start()