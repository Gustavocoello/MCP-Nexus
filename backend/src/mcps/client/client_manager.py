# src/mcps/client/client_manager.py
import os
from typing import Dict, Type
from src.mcps.client.calendar.client_google_calendar import CalendarMCPClient as GoogleCalendarClient
from src.mcps.client.notion.client_notion import NotionMCPClient as NotionClient


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
            }
        }

    def get_client(self, provider_name: str):
        config = self._providers.get(provider_name)
        if not config:
            raise ValueError(f"Proveedor {provider_name} no registrado.")
        
        if not config["url"]:
            raise ValueError(f"La URL para '{provider_name}' no está en las variables de entorno.")
        
        return config["class"](
            url=config["url"], 
            user_id=self.user_id
        )