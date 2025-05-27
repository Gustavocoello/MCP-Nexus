# backend/services/ai_router.py
from openai import OpenAI
from dotenv import load_dotenv
import os, logging

load_dotenv()
logger = logging.getLogger("__name__")

DEEP_API_KEY  = os.getenv("DEEP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QWEN3_API_KEY  = os.getenv("QWEN3_KEY")

API_PROVIDERS = [
    {
        "name": "deepseek",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=DEEP_API_KEY),
        "model": "deepseek/deepseek-chat-v3-0324:free"
    },
    {
        "name": "qwen-3",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=QWEN3_API_KEY),
        "model": "qwen/qwen3-235b-a22b:free"
    },
    {
        "name": "openai",
        "client": OpenAI(api_key=OPENAI_API_KEY),
        "model": "gpt-4o"
    },
    {
        "name": "gemini",
        "client": OpenAI(api_key=GEMINI_API_KEY,
                         base_url="https://generativelanguage.googleapis.com/v1beta/openai/"),
        "model": "gemini-2.0-flash"
    }
]

MAX_RETRIES      = 2          # re-intentos antes de saltar al siguiente proveedor
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
