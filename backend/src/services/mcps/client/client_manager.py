# src/mcps/client/client_manager.py
import os
from src.core.logging import get_logger
from typing import Dict, Type, Optional
from src.database.models.models import UserToken
from src.services.auth.utils.token_crypto import encrypt_token
from src.services.mcps.client.calendar.client_google_calendar import CalendarMCPClient as GoogleCalendarClient
from src.services.mcps.client.notion.client_notion import NotionMCPClient as NotionClient
from src.services.mcps.client.files.client_files import FilesMCPClient as FilesClient
from src.services.mcps.client.github.client_github import GithubMCPClient as GithubClient
from src.services.mcps.client.context.client_context7 import Context7MCPClient as Context7Client

logger = get_logger("mcp_manager")

class MCPClientManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        # Mapeo de proveedores a sus clases específicas
        self._providers = {
            "google_calendar": {
                "class": GoogleCalendarClient,
                "url": os.getenv("MCP_CALENDAR")
            },
            "notion": {
                "class": NotionClient,
                "url": os.getenv("MCP_NOTION")
            },
            "files": {
                "class": FilesClient,
                "url": os.getenv("MCP_FILES")
            },
            "github": {
                "class": GithubClient,
                "url": os.getenv("MCP_GITHUB")
            },
            "context7": {
                "class": Context7Client,
                "url": None # Stdio no usa URL, usa la terminal local de Linux
            }
        }

    def get_client(self, provider_name: str):
        config = self._providers.get(provider_name)
        if provider_name == "context7":
            return config["class"]() # Koda lo instancia limpio
        
        if not config:
            raise ValueError(f"Proveedor {provider_name} no registrado.")
        
        if not config["url"]:
            raise ValueError(f"La URL para '{provider_name}' no está en las variables de entorno.")
        
        return config["class"](
            url=config["url"], 
            user_id=self.user_id
        )