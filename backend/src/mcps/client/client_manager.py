# src/mcps/client_manager.py
import asyncio
from typing import Any, Dict, List, Optional
from .calendar.client_google_calendar import MCPToolsClient as GoogleCalendarClient


class MCPManager:
    """
    Gestor centralizado de clientes MCP.
    Registra todos los clientes disponibles y enruta las herramientas al cliente correcto.
    """
    def __init__(self):
        self._clients = {}  # {client_name: client_class}
        self._tool_to_client_map = {}  # {tool_name: client_name}
        self._initialized = False

    async def initialize(self):
        """Inicializa todos los clientes MCP registrados"""
        if self._initialized:
            return
            
        # Registrar clientes disponibles
        self.register_client("google_calendar", GoogleCalendarClient)
        # En el futuro agregarás más:
        # self.register_client("jira", JiraClient)
        # self.register_client("github", GitHubClient)
        
        # Construir el mapa de herramientas a clientes
        await self._build_tool_mapping()
        self._initialized = True
        
    def register_client(self, client_name: str, client_class):
        """Registra una clase de cliente MCP"""
        self._clients[client_name] = client_class

    async def _build_tool_mapping(self):
        """Construye un mapa que relaciona cada herramienta con su cliente correspondiente"""
        self._tool_to_client_map = {}
        
        for client_name, client_class in self._clients.items():
            # Instanciar temporalmente el cliente para obtener sus herramientas
            temp_client = client_class(user_id="temp_user_for_mapping")
            
            # Obtener la lista de herramientas que este cliente soporta
            if hasattr(temp_client, 'get_supported_tools'):
                supported_tools = await temp_client.get_supported_tools()
            else:
                # Fallback: si el cliente no tiene el método, usar lista vacía
                supported_tools = []
                
            # Mapear cada herramienta al cliente
            for tool_name in supported_tools:
                if tool_name in self._tool_to_client_map:
                    print(f"⚠️ Advertencia: La herramienta '{tool_name}' está duplicada en múltiples clientes")
                self._tool_to_client_map[tool_name] = client_name
                
            # Limpiar
            if hasattr(temp_client, 'close'):
                await temp_client.close()

    async def call_tool(self, tool_name: str, user_id: str, **params) -> Any:
        """
        Llama a una herramienta encontrando el cliente correcto automáticamente.
        """
        if not self._initialized:
            await self.initialize()

        # Limpiar y normalizar el nombre de la herramienta
        tool_name = tool_name.strip()
        
        # Buscar qué cliente maneja esta herramienta
        client_name = self._tool_to_client_map.get(tool_name)
        if not client_name:
            available_tools = list(self._tool_to_client_map.keys())
            raise ValueError(f"No se encontró un cliente MCP para la tool '{tool_name}'. Herramientas disponibles: {available_tools}")

        # Obtener la clase del cliente
        client_class = self._clients.get(client_name)
        if not client_class:
            raise ValueError(f"Cliente '{client_name}' no encontrado")

        # Instanciar el cliente con el user_id correcto
        client_instance = client_class(user_id=user_id)

        # Llamar a la herramienta usando el método genérico _call_tool
        try:
            result = await client_instance._call_tool(tool_name, **params)
            return result
        except Exception as e:
            print(f"Error ejecutando tool '{tool_name}' con cliente '{client_name}': {e}")
            raise

    def get_available_tools(self) -> List[str]:
        """Devuelve la lista de todas las herramientas disponibles"""
        return list(self._tool_to_client_map.keys())

    async def call_tool_with_auth(self, tool_name: str, user_id: str, auth_token: str, **params) -> Any:
        """
        Llama a una herramienta de forma segura, inyectando el JWT de autenticación.
        """
        if not self._initialized:
            await self.initialize()

        tool_name = tool_name.strip()
        
        # Buscar qué cliente maneja esta herramienta
        client_name = self._tool_to_client_map.get(tool_name)
        if not client_name:
            available_tools = list(self._tool_to_client_map.keys())
            raise ValueError(f"No se encontró un cliente MCP para la tool '{tool_name}'. Herramientas disponibles: {available_tools}")

        client_class = self._clients.get(client_name)
        if not client_class:
            raise ValueError(f"Cliente '{client_name}' no encontrado")

        # 🔑 Instanciar el cliente con el user_id y el auth_token
        # (Asumimos que client_class acepta user_id y auth_token en __init__)
        client_instance = client_class(user_id=user_id, auth_token=auth_token) # ⬅️ PASAMOS EL TOKEN

        # Llamar a la herramienta usando el método genérico _call_tool
        try:
            # El _call_tool del cliente ahora usa self.auth_token para el header
            result = await client_instance._call_tool(tool_name, **params)
            return result
        except Exception as e:
            print(f"Error ejecutando tool '{tool_name}' con cliente '{client_name}': {e}")
            raise

# Instancia global del manager
mcp_manager = MCPManager()

