import os
import json
import google.auth.transport.requests
from google.oauth2 import service_account
from openai import OpenAI
from dotenv import load_dotenv

# 1. Cargar variables de entorno (o configurarlas manualmente aquí)
load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "jarvis-endpoint-llm")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
# Ruta al archivo JSON de tu Service Account
GCP_JSON_PATH = os.getenv("GCP_CREDENTIALS_JSON_PATH", "tu-archivo-credenciales.json") 
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
    """Genera un token de acceso fresco. GCP los expira cada 60 min."""
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token

def get_vertex_client(model_id):
    """Configura el cliente de OpenAI para hablar con Vertex AI"""
    base_url = f"https://aiplatform.googleapis.com/v1/projects/{GCP_PROJECT_ID}/locations/{GCP_LOCATION}/endpoints/openapi"
    
    return OpenAI(
        base_url=base_url,
        api_key=get_vertex_token()
    )

# 3. Función de prueba
def test_gemini():
    # El ID 'gemini-1.5-pro-002' es el más estable para la versión 3.1/Pro actual
    model_id = "google/gemini-3.1-pro-preview"
    
    print(f"--- Probando conexión con {model_id} en {GCP_PROJECT_ID} ---")
    
    try:
        client = get_vertex_client(model_id)
        
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "Eres un asistente técnico experto en GCP."},
                {"role": "user", "content": "Hola, confirma que tienes acceso a internet y dime qué modelo eres."}
            ]
        )
        
        print("\n✅ RESPUESTA DEL MODELO:")
        print(response.choices[0].message.content)
        print("\n--- Prueba finalizada con éxito ---")

    except Exception as e:
        print(f"\n❌ ERROR DE CONEXIÓN:")
        print(str(e))

if __name__ == "__main__":
    test_gemini()