import asyncio
from multiprocessing import context
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
import os 
from dotenv import load_dotenv

load_dotenv()

USUARIO_TEST = os.getenv("USUARIO_TEST")

async def main():
    transport = StreamableHttpTransport("http://localhost:8000/mcp-server/mcp/") 
    async with Client(transport=transport) as client:
        await client.ping()
        print("Conexión exitosa al MCP")
        
        # Lista de Tools
        tools = await client.list_tools()
        print("Herramientas disponibles:")
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")
        
        # Ejemplo de llamada a una herramienta
        list_calendars = await client.call_tool("Listar calendarios del usuario", {"context": {"user_id": USUARIO_TEST}})
        print("Calendarios del usuario:", list_calendars)
        
            
if __name__ == "__main__":
    asyncio.run(main())