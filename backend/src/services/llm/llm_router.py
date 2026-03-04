# backend/src/services/llm/llm_router.py
from openai import OpenAI
from dotenv import load_dotenv
import os, logging

load_dotenv()
logger = logging.getLogger("__name__")

# ========== OPEN ROUTER  ==========
OPENROUTER0 = os.getenv("OPEN_ROUTER_0")
OPENROUTER1 = os.getenv("OPEN_ROUTER_1")
OPENROUTER2 = os.getenv("OPEN_ROUTER_2")
OPENROUTER3 = os.getenv("OPEN_ROUTER_3")
OPENROUTER4 = os.getenv("OPEN_ROUTER_4")
OPENROUTER5 = os.getenv("OPEN_ROUTER_5")
OPENROUTER6 = os.getenv("OPEN_ROUTER_6")

# ============== GROQ =============
GROQ_API_KEY0 = os.getenv("GROQ_API_KEY0")
GROQ_API_KEY1 = os.getenv("GROQ_API_KEY1")
GROQ_API_KEY2 = os.getenv("GROQ_API_KEY2")
GROQ_API_KEY3 = os.getenv("GROQ_API_KEY3")

# ========== CLOUDFLARE ==========
# Instance 0
CF_ID_0 = os.getenv("CLOUDFLARE_KEY0")
CF_TOKEN_0 = os.getenv("TOKEN_CLOUDFLARE0")

# Instance 1
CF_ID_1 = os.getenv("CLOUDFLARE_KEY1")
CF_TOKEN_1 = os.getenv("TOKEN_CLOUDFLARE1")

# Instance 2
CF_ID_2 = os.getenv("CLOUDFLARE_KEY2")
CF_TOKEN_2 = os.getenv("TOKEN_CLOUDFLARE2")

# Función auxiliar para construir la URL de Cloudflare
def get_cf_url(account_id):
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"

# ============ COHERE ============
COHORE_API_KEY0 = os.getenv("COHORE_API_KEY0")
COHORE_API_KEY1 = os.getenv("COHORE_API_KEY1")
COHORE_API_KEY2 = os.getenv("COHORE_API_KEY2")
# Cohere usa esta URL para compatibilidad con OpenAI
COHERE_BASE_URL = "https://api.cohere.ai/v1"

# ============ MISTRAL ============
MISTRA_KEY0 = os.getenv("MISTRA_KEY0")

# ============ GEMINI ============
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

API_PROVIDERS = [
    {
        "name": "TNG: R1T Chimera - DeepSeek R1T2 Chimera",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER0),
        "model": "tngtech/deepseek-r1t2-chimera:free"
    },
    {
        "name": "Nemotron Nano 12B",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER1),
        "model": "nvidia/nemotron-nano-12b-v2-vl:free"
    },
    {
        "name": "Amazon: Nova 2 Lite (free",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER2),
        "model": "amazon/nova-2-lite-v1:free"
    },
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
        "name": "Arcee AI: Trinity Large Preview (free)",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER6),
        "model": "arcee-ai/trinity-large-preview:free"
    },
    # ---- BLOQUE GROQ
    {
        "name": "Groq: Llama-3.1-8B-1", 
        "client": OpenAI(base_url="https://api.groq.com/openai/v1", 
                         api_key=GROQ_API_KEY0), 
        "model": "llama-3.1-8b-instant"
    },
    {
        "name": "Groq: Kimi-K2-1", 
        "client": OpenAI(base_url="https://api.groq.com/openai/v1", 
                         api_key=GROQ_API_KEY1), 
        "model": "moonshotai/kimi-k2-instruct"
    },
    {
        "name": "Groq: GPT-OSS-120B-1", 
        "client": OpenAI(base_url="https://api.groq.com/openai/v1", 
                         api_key=GROQ_API_KEY2), 
        "model": "openai/gpt-oss-120b"
    },
    {
        "name": "Groq: Qwen3-32B-1", 
        "client": OpenAI(base_url="https://api.groq.com/openai/v1", 
                         api_key=GROQ_API_KEY3), 
        "model": "qwen/qwen3-32b"
    },
    # ---- BLOQUE CLOUDFLARE
    {
        "name": "Cloudflare: Nodo-Alfa (Llama 3.1)",
        "client": OpenAI(base_url=get_cf_url(CF_ID_0),
                         api_key=CF_TOKEN_0),
        "model": "@cf/meta/llama-3.1-8b-instruct"
    },
    {
        "name": "Cloudflare: Nodo-Beta (LLama 4.0 Scout)",
        "client": OpenAI(base_url=get_cf_url(CF_ID_1), 
                         api_key=CF_TOKEN_1),
        "model": "@cf/meta/llama-4-scout-17b-16e-instruct"
    },
    {
        "name": "Cloudflare: Nodo-Gamma (Qwen 3)",
        "client": OpenAI(base_url=get_cf_url(CF_ID_2), 
                         api_key=CF_TOKEN_2),
        "model": "@cf/qwen/qwen3-30b-a3b-fp8"
    },
    # ---- BLOQUE COHERE
    
    {
        "name": "Cohere: Command-R-Plus (Trial-0)",
        "client": OpenAI(base_url=COHERE_BASE_URL, 
                         api_key=COHORE_API_KEY0),
        "model": "command-r-plus"
    },
    {
        "name": "Cohere: Command-R (Trial-1)",
        "client": OpenAI(base_url=COHERE_BASE_URL, 
                         api_key=COHORE_API_KEY1),
        "model": "command-r"
    },
    {
        "name": "Cohere: Command-R7B (Trial-2)",
        "client": OpenAI(base_url=COHERE_BASE_URL, 
                         api_key=COHORE_API_KEY2),
        "model": "command-r7b"
    },
    # ---- BLOQUE MISTRAL
    {
        "name": "Mistral: Pixtral-Large (Key-0)",
        "client": OpenAI(base_url="https://api.mistral.ai/v1", 
                         api_key=MISTRA_KEY0),
        "model": "pixtral-large-latest"
    },
    {
        "name": "Mistral: Mistral-Small (Key-2)",
        "client": OpenAI(base_url="https://api.mistral.ai/v1", 
                         api_key=MISTRA_KEY0),
        "model": "mistral-small-latest"
    },
    # ------ GEMINI
    {
        "name": "Google: Gemini-1.5-Flash",
        "client": OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=GEMINI_API_KEY
        ),
        "model": "gemini-1.5-flash"
    }
    
]

API_PROVIDERS_TO_AGENT = [
     # ---- BLOQUE OPENROUTER
    {
        "name": "TNG: R1T Chimera - DeepSeek R1T2 Chimera",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER0",
        "model": "tngtech/deepseek-r1t2-chimera:free"
    },
    {
        "name": "Nemotron Nano 12B",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER1",
        "model": "nvidia/nemotron-nano-12b-v2-vl:free"
    },
    {
        "name": "Amazon: Nova 2 Lite (free",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER2",
        "model": "amazon/nova-2-lite-v1:free"
    },
    {
        "name": "TNG: DeepSeek R1T2 Chimera",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER3",
        "model": "tngtech/deepseek-r1t2-chimera:free"
    },
    {
        "name": "Kwaipilot: KAT-Coder-Pro V1",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER4",
        "model": "kwaipilot/kat-coder-pro:free"
    },
    {
        "name": "Qwen: Qwen3 Coder 480B A35B",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER5",
        "model": "qwen/qwen3-coder:free"
    },
    {
        "name": "Arcee AI: Trinity Large Preview (free)",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER6",
        "model": "arcee-ai/trinity-large-preview:free"
    },
    # ---- BLOQUE GROQ
    {
        "name": "Groq: Llama-3.1-8B-1",
        "base_url": "https://api.groq.com/openai/v1",
        "key": "GROQ_API_KEY0",
        "model": "llama-3.1-8b-instant"
    },
    {
        "name": "Groq: Kimi-K2-1",
        "base_url": "https://api.groq.com/openai/v1",
        "key": "GROQ_API_KEY1",
        "model": "moonshotai/kimi-k2-instruct"
    },
    {
        "name": "Groq: GPT-OSS-120B-1",
        "base_url": "https://api.groq.com/openai/v1",
        "key": "GROQ_API_KEY2",
        "model": "openai/gpt-oss-120b"
    },
    {
        "name": "Groq: Qwen3-32B-1",
        "base_url": "https://api.groq.com/openai/v1",
        "key": "GROQ_API_KEY3",
        "model": "qwen/qwen3-32b"
    },
    # ---- BLOQUE CLOUDFLARE
    {
        "name": "Cloudflare: Nodo-Alfa (Llama 3.1)",
        "base_url": "CF_ID_0",  # se resuelve dinámicamente con get_cf_url
        "key": "CF_TOKEN_0",
        "model": "@cf/meta/llama-3.1-8b-instruct"
    },
    {
        "name": "Cloudflare: Nodo-Beta (LLama 4.0 Scout)",
        "base_url": "CF_ID_1",
        "key": "CF_TOKEN_1",
        "model": "@cf/meta/llama-4-scout-17b-16e-instruct"
    },
    {
        "name": "Cloudflare: Nodo-Gamma (Qwen 3)",
        "base_url": "CF_ID_2",
        "key": "CF_TOKEN_2",
        "model": "@cf/qwen/qwen3-30b-a3b-fp8"
    },
    # ---- BLOQUE COHERE
    {
        "name": "Cohere: Command-R-Plus (Trial-0)",
        "base_url": "COHERE_BASE_URL",  # se resuelve dinámicamente
        "key": "COHORE_API_KEY0",
        "model": "command-r-plus"
    },
    {
        "name": "Cohere: Command-R (Trial-1)",
        "base_url": "COHERE_BASE_URL",
        "key": "COHORE_API_KEY1",
        "model": "command-r"
    },
    {
        "name": "Cohere: Command-R7B (Trial-2)",
        "base_url": "COHERE_BASE_URL",
        "key": "COHORE_API_KEY2",
        "model": "command-r7b"
    },
    # ---- BLOQUE MISTRAL
    {
        "name": "Mistral: Pixtral-Large (Key-0)",
        "base_url": "https://api.mistral.ai/v1",
        "key": "MISTRA_KEY0",
        "model": "pixtral-large-latest"
    },
    {
        "name": "Mistral: Mistral-Small (Key-2)",
        "base_url": "https://api.mistral.ai/v1",
        "key": "MISTRA_KEY0",
        "model": "mistral-small-latest"
    },
    # ---- BLOQUE GEMINI
    {
        "name": "Google: Gemini-1.5-Flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key": "GEMINI_API_KEY",
        "model": "gemini-1.5-flash"
    },
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
