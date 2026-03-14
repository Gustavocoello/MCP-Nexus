# src/mcps/client/notion/client_notion.py
from typing import Optional, Dict, List, Any
from ..base_client import BaseMCPClient

class NotionMCPClient(BaseMCPClient):
    """
    Cliente MCP para Notion especializado. 
    Hereda toda la lógica de seguridad y transporte de BaseMCPClient.
    """
    
    def __init__(self, url: Optional[str] = None, user_id: Optional[str] = None):
        # Le pasamos el provider "notion" a la base para que sepa qué JWT generar
        super().__init__(
            url=url, 
            provider="notion", 
            user_id=user_id
        )
    # =================================================================
    #            MÉTODOS WRAPPERS (LAS 9 TOOLS)
    # =================================================================

    # 1. Búsqueda Global
    async def notion_search(self, query: str):
        result = await self._call_server("notion_search", {"query": query})
        return {"data": result.content or [], "success": not result.is_error}

    # 2. Obtener Página
    async def notion_get_page(self, page_id: str):
        result = await self._call_server("notion_get_page", {"page_id": page_id})
        return {"data": result.content or [], "success": not result.is_error}

    # 3. Obtener hijos de un bloque
    async def notion_get_block_children(self, block_id: str):
        result = await self._call_server("notion_get_block_children", {"block_id": block_id})
        return {"data": result.content or [], "success": not result.is_error}

    # 4. Crear Página (en DB o página padre)
    async def notion_create_page(self, parent_id: str, properties: Dict, is_db_parent: bool = True):
        result = await self._call_server("notion_create_page", 
                                            {"parent_id": parent_id, "properties": properties, "is_db_parent": is_db_parent})
        return {"data": result.content or [], "success": not result.is_error}

    # 5. Actualizar Propiedades
    async def notion_update_page_properties(self, page_id: str, properties: Dict):
        result = await self._call_server("notion_update_page_properties", 
                                            {"page_id": page_id, "properties": properties}) 
        return {"data": result.content or [], "success": not result.is_error}

    # 6. Añadir contenido (bloques) a una página/bloque
    async def notion_append_block_children(self, block_id: str, blocks: List[Dict]):
        result = await self._call_server("notion_append_block_children", 
                                            {"block_id": block_id, "blocks": blocks})

        return {"data": result.content or [], "success": not result.is_error}

    # 7. Consultar Base de Datos (Filtros)
    async def notion_query_database(self, database_id: str, filter_params: Optional[Dict] = None):
        result = await self._call_server("notion_query_database", 
                                            {"database_id": database_id, "filter_params": filter_params})
        return {"data": result.content or [], "success": not result.is_error}

    # 8. Obtener Estructura (Esquema) de DB
    async def notion_get_database_structure(self, database_id: str):
        result = await self._call_server("notion_get_database_structure", 
                                            {"database_id": database_id})
        return {"data": result.content or [], "success": not result.is_error}

    # 9. Eliminar (Archivar) bloque
    async def notion_delete_block(self, block_id: str):
        result = await self._call_server("notion_delete_block", 
                                            {"block_id": block_id})
        return {"data": result.content or [], "success": not result.is_error}

# -------------- TEST RÁPIDO --------------
