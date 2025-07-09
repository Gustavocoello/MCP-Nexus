import os
import asyncio
from dotenv import load_dotenv
from huggingface_hub import get_session
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession
from datetime import timedelta

load_dotenv()

SERVER_URL = "http://127.0.0.1:8000/mcp"
USUARIO_TEST = os.getenv("USUARIO_TEST")

async def main():
    url= SERVER_URL
    async with streamablehttp_client(url) as (read, write, get_session_id):

        async with ClientSession(read, write) as session:
            
            print("Session ID:", get_session_id())
            # Listar herramientas registradas en el servidor
            tools = await session.list_tools()
            print("Herramientas disponibles:")
            for t in tools.tools:
                print(f"- {t.name}")

if __name__ == "__main__":
    asyncio.run(main())
