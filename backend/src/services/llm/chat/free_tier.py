# src/services/llm/providers/utils.py
import os
from openai import OpenAI
from dotenv import load_dotenv
from src.core.logging import get_logger 
from src.database.settings.connection import SessionLocal 
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials

# Configuración de logging
logger = get_logger(__name__)

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

OPENROUTER0 = os.getenv("OPEN_ROUTER_0")
OPENROUTER1 = os.getenv("OPEN_ROUTER_1")
OPENROUTER2 = os.getenv("OPEN_ROUTER_2")


AZURE_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT1")
AZURE_KEY = os.getenv("AZURE_KEY1.1")


API_PROVIDERS = [
    {
        'name'     : 'Kwaipilot',
        'client'   : OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key= OPENROUTER0),
        'handler'  : lambda client, prompt: client.chat.completions.create(
            model = 'kwaipilot/kat-coder-pro:free',
            messages = [{'role' : 'user', 'content' : prompt}]
        )
    },
    {
        'name'     : 'Nemotron Nano 12B',
        'client'   : OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key= OPENROUTER1),
        'handler'  : lambda client, prompt: client.chat.completions.create(
            model = 'nvidia/nemotron-nano-12b-v2-vl:free',
            messages = [{'role' : 'user', 'content' : prompt}]
        )
    },
    {
        'name'     : 'TNG: R1T Chimera',
        'client'   : OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key= OPENROUTER1),
        'handler'  : lambda client, prompt: client.chat.completions.create(
            model = 'tngtech/tng-r1t-chimera:free',
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
        if provider["name"] == 'Kwaipilot' and os.getenv('TEST_MODE') == 'True':
            if retry_count == 0:
                raise ConnectionError("Error de conexion simulado con Kwaipilot")
            elif retry_count == 1:
                raise Exception("Error de timeout simulado con Kwaipilot")
            
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
        