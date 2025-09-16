import os
import sys

# Añadir el directorio raíz del proyecto (backend/) al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # backend/
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Ahora puedes importar desde services.ai_providers.utils
try:
    from providers.utils import generate_prompt
    print("Importación exitosa!")
except ImportError as e:
    print(f"Error al importar generate_prompt: {str(e)}")