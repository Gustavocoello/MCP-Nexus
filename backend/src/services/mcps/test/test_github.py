# test_write.py
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
    client = manager.get_client("files")
    try:
        result = await client.write_file(
            file_path="skills/test-write/SKILL.md",
            content="# Test\nEsto es una prueba de escritura."
        )
        print("OK:", result)
    except Exception as e:
        print("FAIL:", type(e).__name__, e)

asyncio.run(test())