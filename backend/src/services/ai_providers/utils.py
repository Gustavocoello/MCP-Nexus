from config.logging_config import get_logger 
from openai import OpenAI
from dotenv import load_dotenv
import os 

# Configuración de logging
logger = get_logger(__name__)

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

DEEP_API_KEY = os.getenv("DEEP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QWEN3_API_KEY = os.getenv("QWEN3_KEY")



API_PROVIDERS = [
    {
        'name'     : 'deepseek',
        'client'   : OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key= DEEP_API_KEY),
        'handler'  : lambda client, prompt: client.chat.completions.create(
            model = 'deepseek/deepseek-chat-v3-0324:free',
            messages = [{'role' : 'user', 'content' : prompt}]
        )
    },
    {
        'name'     : 'qwen-3',
        'client'   : OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key= QWEN3_API_KEY),
        'handler'  : lambda client, prompt: client.chat.completions.create(
            model = 'qwen/qwen3-235b-a22b:free',
            messages = [{'role' : 'user', 'content' : prompt}]
        )
    },
    {
        'name'     : 'openai',
        'client'   : OpenAI(api_key= OPENAI_API_KEY),
        'handler'  : lambda client, prompt : client.chat.completions.create(
            model="gpt-4o",
            messages = [{'role' : 'user', 'content': prompt}]
        )
    },
    {
        'name'     : 'gemini',
        'client'   : OpenAI(
            api_key= GEMINI_API_KEY, 
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"),
        'handler'  : lambda client, prompt: client.chat.completions.create(
            model = 'gemini-2.0-flash',
            messages = [{'role' : 'user', 'content' : prompt}]
        )
    } 
    
    # Se puede añadir más apis aqui para abajo  ->
]

# DeepSeek índice = 0
# Qwen3 índice = 1
# OpenAI índice = 2
# Gemini índice = 3

current_provider_index = 0
MAX_RETRIES = 2 

def generate_prompt(prompt_data, retry_count=0):
    
    logger.debug(f"Modo prueba activado: {os.getenv('TEST_MODE')}")
    
    global current_provider_index
    
    if current_provider_index >= len(API_PROVIDERS):
        return "Todos los servicios de IA no estan disponibles actualmente."
    
    provider = API_PROVIDERS[current_provider_index]
    logger.info(f"usando el {provider['name']} proveedor (Intento {retry_count + 1} /{MAX_RETRIES})")
    
    try:
        # ======================================
        # SIMULADOR DE ERRORES SOLO PARA PRUEBAS
        # ======================================
        if provider["name"] == 'deepseek' and os.getenv('TEST_MODE') == 'True':
            if retry_count == 0:
                raise ConnectionError("Error de conexion simulado con deepseek")
            elif retry_count == 1:
                raise Exception("Error de timeout simulado con deepseek")
            
        user_prompt = prompt_data.get("description", "") # actualizado
        prompt = f"{user_prompt}"
        
        response = provider['handler'](provider['client'], prompt)
        return response.choices[0].message.content 
       
            
    except Exception as e:
        logger.error(f"Error with {provider['name']}: {str(e)}")
        
        """
        Casos que activarán el cambio de proveedor:
            - Errores de conexión (timeout, red caída)
            - Límites de tasa excedidos (rate limits)
            - Errores de autenticación (API key inválida)
            - Errores internos del servidor (5xx)
            - Cualquier excepción no manejada
        """
        
        if retry_count < MAX_RETRIES -1:
            return generate_prompt(prompt_data, retry_count + 1)
        else:
            # Cambiar al siguiente proveedor
            current_provider_index += 1
            return generate_prompt(prompt_data, 0)
        
        