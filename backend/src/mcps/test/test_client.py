# src/mcps/test/test_client.py
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
from src.mcps.client.client_manager import MCPClientManager  # ajusta la ruta si es necesario

load_dotenv()

USUARIO_TEST = os.getenv("USUARIO_TEST")
MCP_URL = os.getenv("MCP")

async def test_integracion():
    manager = MCPClientManager(user_id=USUARIO_TEST)
    
    # Probamos Calendar
    calendar = manager.get_client("google_calendar")
    await calendar.google_listar_calendarios()
    
    # Probamos Notion
    notion = manager.get_client("notion")
    await notion.notion_search(query="Tareas")

    print("✅ Todo fluye por el Manager")

if __name__ == "__main__":
    asyncio.run(test_integracion())