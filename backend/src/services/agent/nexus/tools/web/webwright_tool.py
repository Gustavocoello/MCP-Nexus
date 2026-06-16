import os
import sys
import subprocess
import json
from typing import Optional
from langchain_core.tools import tool
import webwright

WEBWRIGHT_CONFIG_DIR = os.path.join(os.path.dirname(webwright.__file__), "config")
BASE_YAML = os.path.join(WEBWRIGHT_CONFIG_DIR, "base.yaml")

# Tu config mínima — solo el modelo, sin templates
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_YAML = os.path.join(CURRENT_DIR, "model_groq.yaml")

def build_webwright_tools(user_id: str, chat_id: Optional[str] = None, db_session=None):
    """
    Factory: Genera las herramientas de Web Automatization (Webwright) para Nexus.
    """
    provider_name = "webwright"

    def _record_tool_usage(tool_name: str):
        if not db_session or not chat_id: return
        # (Aquí va tu lógica de guardado en base de datos si la usas)
        pass

    @tool
    def webwright_navigate_and_extract(task: str, start_url: str) -> str:
        """
        STRICT WEB AUTOMATION TOOL.
        Uses Webwright (Playwright AI) to navigate a real website, perform actions, and extract data.
        Use this ONLY for web tasks like job searching, scraping, or filling forms.
        Input: task (str) detailing exactly what to extract, start_url (str) the website URL.
        """
        try:
            print(f"\n[WEBWRIGHT] Iniciando en: {start_url}")
            print(f"[WEBWRIGHT] Tarea: {task}")
            
            # --- EL TRUCO DE LAS API KEYS PARA GROQ ---
            env = os.environ.copy()
            
            groq_key = os.getenv("GROQ_API_KEY0")
            if not groq_key:
                return "ERROR CRÍTICO: La llave GROQ_API_KEY0 no está configurada en el .env."
                
            # Engañamos a la librería haciéndole creer que es OpenAI
            env["OPENAI_API_KEY"] = groq_key
            env["OPENAI_BASE_URL"] = "https://api.groq.com/openai/v1"
            # ------------------------------------------

            command = [
                sys.executable, "-m", "webwright.run.cli", "main",
                "-c", BASE_YAML,      # ← templates base de Webwright
                "-c", MODEL_YAML,     # ← tu config de Groq (solo mergea el modelo)
                "-t", task,
                "--start-url", start_url,
                "-o", "outputs/webwright_temp",
            ]

            print("[WEBWRIGHT] Ejecutando navegador... por favor espera.")
            
            # MAGIA AQUÍ: Añadimos cwd=CURRENT_DIR para que la terminal se ubique en esa carpeta
            result = subprocess.run(command, capture_output=True, text=True, env=env, cwd=CURRENT_DIR, creationflags=subprocess.CREATE_NO_WINDOW)
            
            _record_tool_usage("webwright_navigate_and_extract")
            
            # --- MANEJO ESTRICTO DE ERRORES ---
            if result.returncode != 0:
                error_msg = f"ERROR CRÍTICO (Código {result.returncode}) en Webwright:\n{result.stderr}"
                # Lo imprimimos en tu terminal para que tú lo leas
                print(f"\n[WEBWRIGHT FALLÓ] {error_msg}")
                # Se lo devolvemos al LLM para que se detenga
                return error_msg
                
            if not result.stdout.strip():
                error_msg = "ERROR CRÍTICO: Webwright terminó pero no devolvió ningún texto. Revisa los logs de la terminal."
                print(f"\n[WEBWRIGHT FALLÓ] {error_msg}")
                return error_msg

            print("\n[WEBWRIGHT ÉXITO] Datos extraídos correctamente.")
            return f"RESULTADO DE LA EXTRACCIÓN WEB (ENTRÉGALE ESTO AL USUARIO Y DETENTE):\n{result.stdout}"

        except Exception as e:
            error_msg = f"ERROR CRÍTICO: Excepción en Python ejecutando Webwright: {str(e)}"
            print(f"\n[WEBWRIGHT FALLÓ] {error_msg}")
            return error_msg

    return [webwright_navigate_and_extract]