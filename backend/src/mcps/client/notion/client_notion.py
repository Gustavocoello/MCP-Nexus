import os
import json
import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from dotenv import load_dotenv

current_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from src.services.auth.mcp.mcp_jwt import generate_mcp_jwt

load_dotenv()

# Puerto 8002 para Notion
MCP_URL_NOTION = os.getenv("MCP_NOTION") 
USUARIO_TEST = os.getenv("USUARIO_TEST") 

class NotionMCPClient:
    """
    Cliente MCP para Notion con las 9 herramientas del servidor.
    """
    
    SUPPORTED_TOOLS: List[str] = [
        "notion_search",
        "notion_get_page",
        "notion_get_block_children",
        "notion_create_page",
        "notion_update_page_properties",
        "notion_append_block_children",
        "notion_query_database",
        "notion_get_database_structure",
        "notion_delete_block"
    ]

    def __init__(self, url: Optional[str] = None, user_id: Optional[str] = None, auth_token: Optional[str] = None):
        self.url = url or MCP_URL_NOTION
        self.user_id = user_id or USUARIO_TEST
        self.auth_token = auth_token
            
    async def _call_tool_direct(self, tool_name: str, **kwargs) -> Any:
        """Llama al servidor de Notion (Puerto 8002) con el payload de contexto"""
        
        # El servidor espera el context para extraer el user_id/notion_api_key
        payload = {"context": {"user_id": self.user_id}}
        if kwargs:
            payload.update(kwargs)

        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        transport = StreamableHttpTransport(self.url, headers=headers)
        
        async with Client(transport=transport) as client:
            await client.ping()
            result = await client.call_tool(tool_name, payload)
            return result

    # =================================================================
    #            MÉTODOS WRAPPERS (LAS 9 TOOLS)
    # =================================================================

    # 1. Búsqueda Global
    async def notion_search(self, query: str):
        result = await self._call_tool_direct("notion_search", query=query)
        return {"data": result.content or [], "success": not result.is_error}

    # 2. Obtener Página
    async def notion_get_page(self, page_id: str):
        result = await self._call_tool_direct("notion_get_page", page_id=page_id)
        return {"data": result.content or [], "success": not result.is_error}

    # 3. Obtener hijos de un bloque
    async def notion_get_block_children(self, block_id: str):
        result = await self._call_tool_direct("notion_get_block_children", block_id=block_id)
        return {"data": result.content or [], "success": not result.is_error}

    # 4. Crear Página (en DB o página padre)
    async def notion_create_page(self, parent_id: str, properties: Dict, is_db_parent: bool = True):
        result = await self._call_tool_direct("notion_create_page", 
                                            parent_id=parent_id, 
                                            properties=properties, 
                                            is_db_parent=is_db_parent)
        return {"data": result.content or [], "success": not result.is_error}

    # 5. Actualizar Propiedades
    async def notion_update_page_properties(self, page_id: str, properties: Dict):
        result = await self._call_tool_direct("notion_update_page_properties", 
                                            page_id=page_id, 
                                            properties=properties)
        return {"data": result.content or [], "success": not result.is_error}

    # 6. Añadir contenido (bloques) a una página/bloque
    async def notion_append_block_children(self, block_id: str, blocks: List[Dict]):
        result = await self._call_tool_direct("notion_append_block_children", 
                                            block_id=block_id, 
                                            blocks=blocks)
        return {"data": result.content or [], "success": not result.is_error}

    # 7. Consultar Base de Datos (Filtros)
    async def notion_query_database(self, database_id: str, filter_params: Optional[Dict] = None):
        result = await self._call_tool_direct("notion_query_database", 
                                            database_id=database_id, 
                                            filter_params=filter_params)
        return {"data": result.content or [], "success": not result.is_error}

    # 8. Obtener Estructura (Esquema) de DB
    async def notion_get_database_structure(self, database_id: str):
        result = await self._call_tool_direct("notion_get_database_structure", database_id=database_id)
        return {"data": result.content or [], "success": not result.is_error}

    # 9. Eliminar (Archivar) bloque
    async def notion_delete_block(self, block_id: str):
        result = await self._call_tool_direct("notion_delete_block", block_id=block_id)
        return {"data": result.content or [], "success": not result.is_error}

# -------------- TEST RÁPIDO --------------
if __name__ == "__main__":
    async def test():
        mcp_auth_token = generate_mcp_jwt(USUARIO_TEST, "notion")
        client = NotionMCPClient(auth_token=mcp_auth_token)
        print("🚀 Testeando las 9 herramientas de Notion...")
        # Aquí puedes añadir llamadas de prueba
        try:    
            search_results = await client.notion_search(query="Proyectos")
            print(search_results)
        except Exception as e:
            print(f"Error en test: {e}")
        
    asyncio.run(test())