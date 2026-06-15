# test_github_dir.py
import os
import asyncio
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
from src.services.mcps.client.client_manager import MCPClientManager  # ajusta la ruta si es necesario

load_dotenv()

USUARIO_TEST = os.getenv("USUARIO_TEST")

async def test():
    manager = MCPClientManager(user_id=USUARIO_TEST)
    client = manager.get_client("github")
    try:
        result = await client.github_get_file_contents(
            owner="anthropics",
            repo="skills",
            path="skills/frontend-design",
            branch="main"
        )
        print("OK:", str(result)[:500])
    except Exception as e:
        print("FAIL:", e)

asyncio.run(test())