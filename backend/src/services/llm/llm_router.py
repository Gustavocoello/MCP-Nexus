# backend/src/services/llm/llm_router.py
import os, logging
import json
from openai import OpenAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
# CLOUD GCP
from google.oauth2 import service_account
import google.auth.transport.requests

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
GROQ_API_KEY4 = os.getenv("GROQ_API_KEY4")
GROQ_API_KEY5 = os.getenv("GROQ_API_KEY5")

# ========== CLOUDFLARE ==========
# Instance 0
CF_ID_0 = os.getenv("CLOUDFLARE_ID0")
CF_TOKEN_0 = os.getenv("CLOUDFLARE_TOKEN0")

# Instance 1
CF_ID_1 = os.getenv("CLOUDFLARE_ID1")
CF_TOKEN_1 = os.getenv("CLOUDFLARE_TOKEN1")

# Instance 2
CF_ID_2 = os.getenv("CLOUDFLARE_ID2")
CF_TOKEN_2 = os.getenv("CLOUDFLARE_TOKEN2")

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

# CLOUD GCP - para gemini de pago (eliminar antes del 29-05-2026)
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION")
GCP_JSON_PATH = os.getenv("GCP_CREDENTIALS_JSON_PATH") 

VERTEX_BASE_URL = f"https://aiplatform.googleapis.com/v1/projects/{GCP_PROJECT_ID}/locations/{GCP_LOCATION}/endpoints/openapi"
# Cargar crendenciales json PATH_TO_JSON = "tu-archivo-credenciales.json" 
gcp_json_str = GCP_JSON_PATH
# 2. Configuración de Seguridad y Tokens
if gcp_json_str:
    try:
        # Convertimos el string del .env en un diccionario de Python
        info = json.loads(gcp_json_str)
        
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        print("Credenciales cargadas exitosamente desde el .env")
    except Exception as e:
        print(f"Error al procesar el JSON del .env: {e}")
        
def get_vertex_token():
    """Genera un token fresco para Vertex AI"""
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token

API_PROVIDERS = [
    # ------ GEMINI DE PAGO (GCP) - eliminar antes del 29-05-2026
    {
        "name": "Google: gemini-3.1-pro-preview (Trial)",
        "client": OpenAI(base_url=VERTEX_BASE_URL,
                         api_key=get_vertex_token()
                         ),
        "model": "google/gemini-3.1-pro-preview"
    },
    # ---- BLOQUE OPENROUTER
    {
        "name": "openrouter0",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER0),
        "model": "openrouter/free"
    },
    {
        "name": "openrouter1",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER1),
        "model": "openrouter/free"
    },
    {
        "name": "openrouter2",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER2),
        "model": "openrouter/free"
    },
    {
        "name": "openrouter3",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER3),
        "model": "openrouter/free"
    },
    {
        "name": "openrouter4",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER4),
        "model": "openrouter/free"
    },
    {
        "name": "openrouter5",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER5),
        "model": "openrouter/free"
    },
    {
        "name": "openrrouter6",
        "client": OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=OPENROUTER6),
        "model": "openrouter/free"
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
    {
        "name": "Groq: Qwen3-32B-1", 
        "client": OpenAI(base_url="https://api.groq.com/openai/v1", 
                         api_key=GROQ_API_KEY4), 
        "model": "qwen/qwen3-32b"
    },{
        "name": "Groq: Qwen3-32B-1", 
        "client": OpenAI(base_url="https://api.groq.com/openai/v1", 
                         api_key=GROQ_API_KEY5), 
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
        "model": "command-r-08-2024"
    },
    {
        "name": "Cohere: Command-R-plus (Trial-1)",
        "client": OpenAI(base_url=COHERE_BASE_URL, 
                         api_key=COHORE_API_KEY1),
        "model": "command-r-plus-08-2024"
    },
    {
        "name": "Cohere: Command-R-plus (Trial-2)",
        "client": OpenAI(base_url=COHERE_BASE_URL, 
                         api_key=COHORE_API_KEY2),
        "model": "command-r-plus-08-2024"
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
    }
    
]

API_PROVIDERS_TO_AGENT = [
    # ------ GEMINI DE PAGO (GCP) - eliminar antes del 29-05-2026
    {
        "name": "Google: gemini-3.1-pro-preview (Trial)",
        "base_url": VERTEX_BASE_URL,
        "key_func": get_vertex_token,
        "model": "google/gemini-3.1-pro-preview"
    }, 
     # ---- BLOQUE OPENROUTER
    {
        "name": "OPENROUTER - FREE 0",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER0",
        "model": "openrouter/free"
    },
    {
        "name": "OPENROUTER - FREE 1",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER1",
        "model": "openrouter/free"
    },
    {
        "name": "OPENROUTER - FREE 2",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER2",
        "model": "openrouter/free"
    },
    {
        "name": "OPENROUTER - FREE 3",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER3",
        "model": "openrouter/free"
    },
    {
        "name": "OPENROUTER - FREE 4",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER4",
        "model": "openrouter/free"
    },
    {
        "name": "OPENROUTER - FREE 5",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER5",
        "model": "openrouter/free"
    },
    {
        "name": "OPENROUTER - FREE 6",
        "base_url": "https://openrouter.ai/api/v1",
        "key": "OPENROUTER6",
        "model": "openrouter/free"
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
        "model": "qwen/qwen3-32b"
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
        "model": "llama-3.3-70b-versatile"
    },
    {
        "name": "Groq: Qwen3-32B-1",
        "base_url": "https://api.groq.com/openai/v1",
        "key": "GROQ_API_KEY4",
        "model": "qwen/qwen3-32b"
    },
    {
        "name": "Groq: Qwen3-32B-1",
        "base_url": "https://api.groq.com/openai/v1",
        "key": "GROQ_API_KEY5",
        "model": "llama-3.3-70b-versatile"
    },
    # ---- BLOQUE CLOUDFLARE
    {
        "name": "Cloudflare: Nodo-Alfa (Llama 3.1)",
        "base_url": "CLOUDFLARE_ID0",  # se resuelve dinámicamente con get_cf_url
        "key": "CLOUDFLARE_TOKEN0",
        "model": "@cf/meta/llama-3.1-8b-instruct"
    },
    {
        "name": "Cloudflare: Nodo-Beta (LLama 4.0 Scout)",
        "base_url": "CLOUDFLARE_ID1",
        "key": "CLOUDFLARE_TOKEN1",
        "model": "@cf/meta/llama-4-scout-17b-16e-instruct"
    },
    {
        "name": "Cloudflare: Nodo-Gamma (Qwen 3)",
        "base_url": "CLOUDFLARE_ID2",
        "key": "CLOUDFLARE_TOKEN2",
        "model": "@cf/qwen/qwen3-30b-a3b-fp8"
    },
    # ---- BLOQUE COHERE
    {
        "name": "Cohere: Command-R-Plus (Trial-0)",
        "base_url": "https://api.cohere.ai/compatibility/v1",  # se resuelve dinámicamente
        "key": "COHORE_API_KEY0",
        "model": "command-r-08-2024"
    },
    {
        "name": "Cohere: Command-R-Plus (Trial-1)",
        "base_url": "https://api.cohere.ai/compatibility/v1",
        "key": "COHORE_API_KEY1",
        "model": "command-r-plus-08-2024"
    },
    {
        "name": "Cohere: Command-R-Plus (Trial-2)",
        "base_url": "https://api.cohere.ai/compatibility/v1",
        "key": "COHORE_API_KEY2",
        "model": "command-r-plus-08-2024"
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
            # 1. EVALUACIÓN DINÁMICA DE LA LLAVE O KEY
            if "key_func" in prov:
                # Si tiene key_func, llamamos a la función con () para generar un token nuevo
                api_key = prov["key_func"]() 
            else:
                # Si no, simplemente usamos la llave estática que guardamos
                api_key = prov["key"]
            
            # 2. RECONSTRUCCIÓN DEL CLIENTE CON LA LLAVE ACTUALIZADA
            client = OpenAI(
                base_url=prov["base_url"],
                api_key=api_key
            )
            # 3. LLAMADA A LA API
            resp = client.chat.completions.create(
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
            # 1. EVALUACIÓN DINÁMICA DE LA LLAVE
            if "key_func" in prov:
                api_key = prov["key_func"]() 
            else:
                api_key = prov["key"]
            # 2. RECONSTRUCCIÓN DEL CLIENTE
            client = OpenAI(
                base_url=prov["base_url"],
                api_key=api_key
            )
            # 3. LLAMADA A LA API CON STREAMING
            resp = client.chat.completions.create(
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

# Agentes
def get_langchain_llm(temperature: int = 0) -> ChatOpenAI:
    """
    Itera API_PROVIDERS_TO_AGENT en orden y devuelve el primer
    ChatOpenAI que se pueda construir con key válida.
    """
    for prov in API_PROVIDERS_TO_AGENT:
        
        # Resolver la key
        if "key_func" in prov:
            try:
                api_key = prov["key_func"]()
            except Exception:
                continue
        else:
            api_key = os.getenv(prov["key"])
        
        if not api_key:
            continue

        # Resolver base_url (Cloudflare tiene ID en el campo)
        base_url = prov["base_url"]
        if base_url.startswith("CLOUDFLARE_ID"):
            cf_id = os.getenv(base_url)  # base_url es el nombre de la env var
            if not cf_id:
                continue
            base_url = get_cf_url(cf_id)

        try:
            return ChatOpenAI(
                base_url=base_url,
                api_key=api_key,
                model=prov["model"],
                temperature=temperature
            )
        except Exception:
            continue

    raise RuntimeError("No hay providers LLM disponibles para LangChain")