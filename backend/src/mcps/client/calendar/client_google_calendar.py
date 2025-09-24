# src/mcps/client/calendar/client_google_calendar.py

from http import server
import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import date as _date

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from dotenv import load_dotenv

load_dotenv()

MCP_URL = os.getenv("MCP")  
USUARIO_TEST = os.getenv("USUARIO_TEST")  


class MCPToolsClient:
    """
    Cliente MCP que:
    - Acepta nombres como llegan del frontend (corto/largo).
    - Inserta siempre context.user_id.
    - Llama a la tool del servidor con su nombre real.
    """
    
    SUPPORTED_TOOLS: List[str] = [
    "google_resumen_diario",
    "google_resumen_semanal",
    "google_disponibilidad_diaria",
    "google_disponibilidad_semanal",
    "google_listar_calendarios"
    ]

    def __init__(self, url: Optional[str] = None, user_id: Optional[str] = None):
        self.url = url or MCP_URL
        if not self.url:
            raise ValueError("MCP_URL no configurado. Define la variable de entorno MCP.")
        self.transport = StreamableHttpTransport(self.url)
        self.user_id = user_id or USUARIO_TEST
        if not self.user_id:
            raise ValueError("USUARIO_TEST no configurado. Define la variable de entorno USUARIO_TEST o pasa user_id.")

        self._discovered_tools = {}
            
    def _save_auto_tool(self, frontend_name: str, server_name: str):
        """Guarda herramienta descubierta automáticamente SOLO si comienza con google_"""
        # Solo procesar tools que comiencen con "google_"
        if frontend_name.startswith("google_"):
            # Solo agregar a SUPPORTED_TOOLS si no existe
            if frontend_name not in self.SUPPORTED_TOOLS:
                self.SUPPORTED_TOOLS.append(frontend_name)
                print(f" Tool Google '{frontend_name}' añadida automáticamente")
            else:
                print(f" Tool Google '{frontend_name}' ya existe en SUPPORTED_TOOLS")
        else:
            print(f" Tool '{frontend_name}' ignorada (no comienza con 'google_')")
    
    async def _call_tool(self, tool_display_name: str, **kwargs) -> Any:
        """
        tool_display_name: como llega del frontend (corto o largo)
        kwargs: parámetros adicionales de la tool
        AUTO-DISCOVERY: Si la tool no está en TOOLS_MAP pero funciona, se añade automáticamente
        """
        # Normalizamos clave y resolvemos nombre real del servidor
        key = (tool_display_name or "").strip()

        # Verificamos si es una tool de google
        if not key.startswith("google_"):
            raise ValueError(f"Tool '{key}' no permitida (solo se aceptan tools que empiezan con 'google_').")
        
        # Si existe un wrapper con el mismo nombre → usarlo
        if hasattr(self, key) and callable(getattr(self, key)):
            wrapper_func = getattr(self, key)
            print(f" Usando wrapper para tool '{key}'")
            return await wrapper_func(**kwargs)

        # Si no hay wrapper → fallback a llamada directa al servidor MCP
        
        # Verificamos si es nueva tool o no estaba en el mapa
        server_tool_name = key  
        is_new_tool = key not in self.SUPPORTED_TOOLS

        payload = {"context": {"user_id": self.user_id}}
        if kwargs:
            payload.update(kwargs)

        async with Client(transport=self.transport) as client:
            await client.ping()
            try:
                result = await client.call_tool(server_tool_name, payload)
                # Si era una herramienta nueva y funciona!, la guardamos automáticamente
                if is_new_tool and not getattr(result, 'is_error', False):
                    self._save_auto_tool(key, server_tool_name)
                                
                return result
                
            except Exception as e:
                # Si falla una herramienta que no estaba en el mapa, registramos el error
                if is_new_tool:
                    print(f"Tool nueva '{key}' falló: {e}")
                raise
            
    async def _call_tool_direct(self, tool_display_name: str, **kwargs) -> Any:
        """
        Llama siempre al servidor, sin intentar usar wrappers locales.
        """
        key = (tool_display_name or "").strip()

        if not key.startswith("google_"):
            raise ValueError(f"Tool '{key}' no permitida (solo se aceptan tools que empiezan con 'google_'.")

        payload = {"context": {"user_id": self.user_id}}
        if kwargs:
            payload.update(kwargs)

        async with Client(transport=self.transport) as client:
            await client.ping()
            result = await client.call_tool(key, payload)

            if key not in self.SUPPORTED_TOOLS and not getattr(result, "is_error", False):
                self._save_auto_tool(key, key)

            return result

        
    async def get_supported_tools(self) -> List[str]:
        """Devuelve la lista EXPLÍCITA de herramientas soportadas por este cliente"""
        return self.SUPPORTED_TOOLS.copy()

    # ---------- TOOLS SENCILLAS ----------

    async def google_listar_calendarios(self):
        # Acepta tanto alias corto como largo
        result = await self._call_tool_direct("google_listar_calendarios")
        return {
            "prompt": "This is a MCP Tools response to google calendar information.",
            "data": result.content or [],
        }
        

    async def google_resumen_diario(self, calendar_id: Optional[str] = None):
        # Si no se pasa calendar_id, usar "" -> todos los calendarios
        result = await self._call_tool_direct("google_resumen_diario", calendar_id=calendar_id or "")
        return {
            "prompt": "This is a MCP Tools response to google calendar information.",
            "data": result.content or [],
        }

    async def google_resumen_semanal(self, calendar_id: Optional[str] = None):
        result = await self._call_tool_direct("google_resumen_semanal", calendar_id=calendar_id or "")
        return {
            "prompt": "This is a MCP Tools response to google calendar information.",
            "data": result.content or [],
        }

    async def google_disponibilidad_diaria(self, date: Optional[str] = None, duration_minutes: int = 60):
        args = {"duration_minutes": duration_minutes}
        if date:
            args["date"] = date

        # Llamas la tool por su nombre exacto
        result = await self._call_tool_direct("google_disponibilidad_diaria", **args)
        # result puede ser un ToolResult con contenido y structured_content

        # Parseas la respuesta para front
        # Ejemplo: devolver líneas legibles + la estructura
        content_blocks = []
        if result.content:
            # result.content es lista de bloques de texto
            for cb in result.content:
                # tipo cb puede ser objeto con .text
                if hasattr(cb, "text"):
                    content_blocks.append(cb.text)
                else:
                    # si es dict u otro tipo
                    content_blocks.append(str(cb))
        structured = result.structured_content.get("result", []) if result.structured_content else []

        return {
            "success": not result.is_error,
            "lines": content_blocks,
            "slots": structured
        }

    async def google_disponibilidad_semanal(self, duration_minutes: int = 60):
        args = {"duration_minutes": duration_minutes}

        result = await self._call_tool_direct("google_disponibilidad_semanal", **args)

        content_blocks = []
        if result.content:
            for cb in result.content:
                if hasattr(cb, "text"):
                    content_blocks.append(cb.text)
                else:
                    content_blocks.append(str(cb))
        structured = result.structured_content.get("result", []) if result.structured_content else []

        return {
            "success": not result.is_error,
            "lines": content_blocks,
            "weekly": structured
        }


# -------------- TEST RÁPIDO --------------
if __name__ == "__main__":
    async def main():
        client = MCPToolsClient()

        print("📌 Listando calendarios...")
        calendars = await client.listar_calendarios()
        print(calendars)

        print("\n📌 Resumen diario...")
        resumen_d = await client.resumen_diario()  # usa primary por defecto
        print(resumen_d)

        print("\n📌 Resumen semanal...")
        resumen_s = await client.resumen_semanal()
        print(resumen_s)
        
        print("\n📌 Eventos por título (keyword='reunión')...")
        eventos = await client.eventos_por_titulo(keyword="reunión")
        print(eventos)

    asyncio.run(main())
