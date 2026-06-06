import os
import json
import google.auth.transport.requests
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage
from google.oauth2 import service_account
from openai import OpenAI
from dotenv import load_dotenv

# 1. Cargar variables de entorno (o configurarlas manualmente aquí)
load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION")
# Ruta al archivo JSON de tu Service Account
GCP_JSON_PATH = os.getenv("GCP_CREDENTIALS_JSON_PATH") 
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
        
        print("\n RESPUESTA DEL MODELO:")
        print(response.choices[0].message.content)
        print("\n--- Prueba finalizada con éxito ---")

    except Exception as e:
        print(f"\n ERROR DE CONEXIÓN:")
        print(str(e))
        
        

def test_vertex_openai_toolcalling():
    """Usa la vía OpenAI-compatible de Vertex (la que YA funciona) con tool calling"""
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool

    print(f"\n--- Probando Vertex vía ChatOpenAI con tool calling ---")

    @tool
    def suma(a: int, b: int) -> int:
        """Suma dos números."""
        return a + b

    try:
        llm = ChatOpenAI(
            base_url=f"https://aiplatform.googleapis.com/v1/projects/{GCP_PROJECT_ID}/locations/{GCP_LOCATION}/endpoints/openapi",
            api_key=get_vertex_token(),   # el token fresco de tu service account
            model="google/gemini-3.1-pro-preview",
            temperature=0,
        ).bind_tools([suma])

        resp = llm.invoke([HumanMessage(content="¿Cuánto es 99 + 1?")])

        if resp.tool_calls:
            print(f"Tool calling FUNCIONA: {resp.tool_calls}")
        else:
            print(f"Respondió sin tool: {resp.content}")

    except Exception as e:
        print(f"\nERROR: {e}")


if __name__ == "__main__":
    #test_gemini()
    test_vertex_openai_toolcalling()
    