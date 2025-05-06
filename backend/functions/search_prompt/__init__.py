import os
import sys
import json
import logging

from openai import project  
from function_app import app
import azure.functions as func

# Configurar logging
logger = logging.getLogger(__name__)

"""
Esta parte funciona en local, pero no en Azure Functions.
# Esto es para que funcione en local, ya que la estructura de carpetas es diferente
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # backend/
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print("Ruta del proyecto agregada a sys.path:", project_root)

# Ahora puedes importar desde services.ai_providers.utils
try:
    from src.services.ai_providers.utils import generate_prompt
    print("Importación exitosa!")
except ImportError as e:
    print(f"Error al importar generate_prompt: {str(e)}")
"""

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..")) # Sube dos niveles para llegar a backend -> search_prompt/functions/backend

try:
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from src.services.ai_providers.utils import generate_prompt
    print("generate_prompt importado desde src.services.ai_providers.utils")
except ImportError as e:
    print(f"No se pudo importar desde src.services.ai_providers.utils: {e}")
    # Intentar importar generate_prompt desde un módulo local en functions
    try:
        from utils import generate_prompt
        logger.info("generate_prompt importado desde utils.py en functions")
    except ImportError as e2:
        logger.error(f"No se pudo importar generate_prompt desde ninguna ubicación: {e2}")
        raise
# Azure functions
# App = func.FunctionApp() -> viene desde function_app.py
#@app.route(route="search/prompt", auth_level=func.AuthLevel.FUNCTION) no necesarios 
def search_prompt_func(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        
        if not body or "prompt" not in body:
            logger.error("No prompt received")
            return func.HttpResponse(
                json.dumps({"error": "Prompt is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"Prompt recibido: {body['prompt']}")
        result = generate_prompt({"description": body["prompt"]})
        
        if result == "Todos los servicios de IA no están disponibles actualmente.":
            return func.HttpResponse(
                json.dumps({"error": result}),
                status_code=500,
                mimetype="application/json"
            )
            
        return func.HttpResponse(
            json.dumps({"result": result}),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        error_msg = f"Error procesando el prompt: {str(e)}"
        logger.error(error_msg)
        return func.HttpResponse(
            json.dumps({"error": error_msg}),
            status_code=500,
            mimetype="application/json"
        )