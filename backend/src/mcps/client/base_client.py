# src/mcps/client/base_client.py
import os
from typing import Any, Dict, Optional
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from src.services.auth.mcp.mcp_jwt import generate_mcp_jwt

class BaseMCPClient:
    def __init__(self, url: str, provider: str, user_id: str):
        self.url = url
        self.provider = provider
        self.user_id = user_id

    async def _call_server(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Motor único de ejecución para todos los MCPs"""
        # 1. Generar identidad centralizada
        token = generate_mcp_jwt(self.user_id, self.provider)
        if not token:
            raise PermissionError(f"No se pudo autorizar al proveedor {self.provider}")

        # 2. Configurar transporte con el JWT
        headers = {"Authorization": f"Bearer {token}"}
        transport = StreamableHttpTransport(self.url, headers=headers)

        # 3. Llamada limpia al servidor
        async with Client(transport=transport) as client:
            return await client.call_tool(tool_name, arguments)