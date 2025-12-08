# backend/services/ai_router.py
from openai import OpenAI
from dotenv import load_dotenv
import os, logging

load_dotenv()
logger = logging.getLogger("__name__")

OPENROUTER2 = os.getenv("OPEN_ROUTER_2")
OPENROUTER3 = os.getenv("OPEN_ROUTER_3")
OPENROUTER4 = os.getenv("OPEN_ROUTER_4")
OPENROUTER5 = os.getenv("OPEN_ROUTER_5")

API_PROVIDERS = [
    {
        "name": "TNG: DeepSeek R1T2 Chimera",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER3),
        "model": "tngtech/deepseek-r1t2-chimera:free"
    },
    {
        "name": "Kwaipilot: KAT-Coder-Pro V1",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER4),
        "model": "kwaipilot/kat-coder-pro:free"
    },
    {
        "name": "Qwen: Qwen3 Coder 480B A35B",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER5),
        "model": "qwen/qwen3-coder:free"
    },
    {
        "name": "Amazon: Nova 2 Lite (free",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER2),
        "model": "amazon/nova-2-lite-v1:free"
    }
]

MAX_RETRIES      = 3          # re-intentos antes de saltar al siguiente proveedor
_provider_index  = 0          # estado global sencillo

def completion(messages):
    """
    Llama a la API con rotación automática. Recibe `messages` estilo OpenAI.
    Devuelve el string respuesta del assistant.
    """
    global _provider_index
    retries = 0

    while _provider_index < len(API_PROVIDERS):
        prov = API_PROVIDERS[_provider_index]
        logger.info(f"Usando provider '{prov['name']}'  (reintento {retries+1})")

        try:
            resp = prov["client"].chat.completions.create(
                model=prov["model"],
                messages=messages
            )
            # éxito: no cambiamos índice
            return resp.choices[0].message.content.strip()

        except Exception as err:
            logger.error(f"Provider '{prov['name']}' falló: {err}")
            if retries < MAX_RETRIES - 1:
                retries += 1
                continue      # nuevo intento con el mismo proveedor
            # agoté reintentos → next provider
            _provider_index += 1
            retries = 0

    raise RuntimeError("Todos los proveedores fallaron ─ intenta más tarde.")


def completion_stream(messages):
    """
    Igual a `completion`, pero retorna chunks progresivos con stream=True.
    Es un generador.
    """
    global _provider_index
    retries = 0

    while _provider_index < len(API_PROVIDERS):
        prov = API_PROVIDERS[_provider_index]
        logger.info(f"[STREAMING] Usando provider '{prov['name']}' (reintento {retries+1})")

        try:
            # chunk - streaming
            resp = prov["client"].chat.completions.create(
                model=prov["model"],
                messages=messages,
                stream=True
            )

            for chunk in resp:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

            return  # salgo después de terminar el yield

        except Exception as err:
            logger.error(f"[STREAMING] Provider '{prov['name']}' falló: {err}")
            if retries < MAX_RETRIES - 1:
                retries += 1
                continue
            _provider_index += 1
            retries = 0

    raise RuntimeError("Todos los proveedores fallaron ─ intenta más tarde.")
