import os 
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# --- Path Fix ---
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# --- Imports del proyecto ---
from src.mcps.client.calendar.client_google_calendar import MCPToolsClient  # ajusta la ruta si es necesario

load_dotenv()

USUARIO_TEST = os.getenv("USUARIO_TEST")
MCP_URL = os.getenv("MCP")

async def test_disponibilidades():
    client = MCPToolsClient(MCP_URL, user_id=USUARIO_TEST)

    print("== Test: Disponibilidad Diaria (sin parámetros) ==")
    result_diaria = await client.google_disponibilidad_diaria()  # sin mandar date ni duracion
    print("Contenido diaria:", result_diaria)

    print("== Test: Disponibilidad Semanal ==")
    result_semanal = await client.google_disponibilidad_semanal()  # sin parámetros
    print("Contenido semanal:", result_semanal)


if __name__ == "__main__":
    asyncio.run(test_disponibilidades())
