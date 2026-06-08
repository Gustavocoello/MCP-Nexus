# src/mcps/client/base_client.py
import os
from typing import Any, Dict, Optional
from fastmcp import Client
from langchain_core.tools import StructuredTool
from fastmcp.client.transports import StreamableHttpTransport
from src.services.auth.mcp.mcp_jwt import generate_mcp_jwt

class BaseMCPClient:
    def __init__(self, url: str, provider: str, user_id: str):
        self.url = url
        self.provider = provider
        self.user_id = user_id
        self._active_client: Optional[Client] = None  # Almacena la sesión viva

    async def __aenter__(self):
        """Abre la conexión y la mantiene abierta en memoria (Optimización)"""
        token = generate_mcp_jwt(self.user_id, self.provider)
        if not token:
            raise PermissionError(f"No se pudo autorizar al proveedor {self.provider}")

        headers = {"Authorization": f"Bearer {token}"}
        transport = StreamableHttpTransport(self.url, headers=headers)
        
        self._active_client = Client(transport=transport)
        await self._active_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierra la conexión al salir del bloque"""
        if self._active_client:
            await self._active_client.__aexit__(exc_type, exc_val, exc_tb)
            self._active_client = None
            
    async def get_langchain_tools(self) -> list[StructuredTool]:
        """
        Consulta al servidor MCP cuáles son sus herramientas y devuelve una lista 
        de StructuredTools para inyectar en la documentación o en LangChain.
        """
        if self._active_client:
            mcp_tools_response = await self._active_client.list_tools()
        else:
            token = generate_mcp_jwt(self.user_id, self.provider)
            if not token:
                raise PermissionError(f"No se pudo autorizar al proveedor {self.provider}")
                
            headers = {"Authorization": f"Bearer {token}"}
            transport = StreamableHttpTransport(self.url, headers=headers)
            async with Client(transport=transport) as client:
                mcp_tools_response = await client.list_tools()

        # MANEJO INFALIBLE DE LA RESPUESTA
        if isinstance(mcp_tools_response, list):
            tools_list = mcp_tools_response
        elif hasattr(mcp_tools_response, "tools"):
            tools_list = mcp_tools_response.tools
        elif isinstance(mcp_tools_response, dict):
            tools_list = mcp_tools_response.get("tools", [])
        else:
            tools_list = []

        langchain_tools = []
        for mcp_tool in tools_list:
            # Extraer de forma segura sea un objeto o diccionario
            if isinstance(mcp_tool, dict):
                name = mcp_tool.get("name", "unknown")
                desc = mcp_tool.get("description", "")
            else:
                name = getattr(mcp_tool, "name", "unknown")
                desc = getattr(mcp_tool, "description", "")
            # Asegurar que hay descripción
            if not desc: desc = "Herramienta expuesta vía MCP"
            
            langchain_tools.append(
                StructuredTool.from_function(
                    coroutine=lambda **kwargs: None, 
                    name=name.replace("-", "_"),
                    description=desc
                )
            )
            
        return langchain_tools

    async def _call_server(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Motor único: Usa la sesión viva si existe, si no, abre una temporal"""
        if self._active_client:
            return await self._active_client.call_tool(tool_name, arguments)
        
        token = generate_mcp_jwt(self.user_id, self.provider)
        if not token:
            raise PermissionError(f"No tienes vinculada la cuenta de {self.provider}.")
        headers = {"Authorization": f"Bearer {token}"}
        transport = StreamableHttpTransport(self.url, headers=headers)
        async with Client(transport=transport) as client:
            return await client.call_tool(tool_name, arguments)