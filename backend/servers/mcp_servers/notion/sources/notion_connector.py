import httpx
from typing import Optional, Dict, List, Any

class NotionConnector:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    async def _request(self, method: str, endpoint: str, json_data: Optional[Dict] = None):
        """Manejador central de peticiones asíncronas"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}/{endpoint}"
            response = await client.request(method, url, headers=self.headers, json=json_data)
            response.raise_for_status()
            return response.json()

    # --- 1. notion_search ---
    async def search(self, query: str):
        payload = {"query": query, "sort": {"direction": "descending", "timestamp": "last_edited_time"}}
        return await self._request("POST", "search", payload)

    # --- 2. notion_get_page ---
    async def get_page(self, page_id: str):
        return await self._request("GET", f"pages/{page_id}")

    # --- 3. notion_get_block_children ---
    async def get_block_children(self, block_id: str):
        """Lee el contenido. Si hay más de 100 bloques, podrías iterar aquí."""
        # Limpiamos el ID por si acaso
        clean_id = block_id.replace("-", "")
        return await self._request("GET", f"blocks/{clean_id}/children")

    # --- 4. notion_create_page ---
    async def create_page(self, parent_id: str, properties: Dict, is_db_parent: bool = True):
        parent_type = "database_id" if is_db_parent else "page_id"
        payload = {"parent": {parent_type: parent_id}, "properties": properties}
        return await self._request("POST", "pages", payload)

    # --- 5. notion_update_page_properties ---
    async def update_page_properties(self, page_id: str, properties: Dict):
        return await self._request("PATCH", f"pages/{page_id}", {"properties": properties})

    # --- 6. notion_append_block_children ---
    async def append_block_children(self, block_id: str, blocks: List[Dict]):
        return await self._request("PATCH", f"blocks/{block_id}/children", {"children": blocks})

    # --- 7. notion_query_database ---
    async def query_database(self, database_id: str, filter_params: Optional[Dict] = None):
        """
        Consulta tus tablas con muchas columnas. 
        Permite enviar filtros complejos desde Lamar.
        """
        body = {}
        if filter_params:
            # Si el LLM manda el filtro sin el wrapper "filter", lo agregamos
            if "filter" not in filter_params and ("property" in filter_params or "and" in filter_params or "or" in filter_params):
                body["filter"] = filter_params
            else:
                body.update(filter_params)
        
        return await self._request("POST", f"databases/{database_id}/query", json_data=body)

    # --- 8. notion_get_database_structure ---
    async def get_database_structure(self, database_id: str):
        return await self._request("GET", f"databases/{database_id}")

    # --- 9. notion_delete_block ---
    async def delete_block(self, block_id: str):
        return await self._request("DELETE", f"blocks/{block_id}")