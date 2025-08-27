# src/mcps/client/calendar/client_google_calendar.py

import os
import asyncio
from typing import Optional, Dict, Any
from datetime import date as _date

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from dotenv import load_dotenv

load_dotenv()

MCP_URL = os.getenv("MCP")  # ej: http://localhost:8000/mcp-server/mcp/
USUARIO_TEST = os.getenv("USUARIO_TEST")  # fallback para pruebas locales

# El frontend puede mandar NOMBRE CORTO o LARGO.
# Mapeamos ambos al nombre REGISTRADO EN EL SERVIDOR MCP.
TOOLS_MAP: Dict[str, str] = {
    # --- Listar calendarios ---
    "listar_calendarios": "Listar calendarios del usuario",
    "Listar calendarios del usuario": "Listar calendarios del usuario",

    # --- Resúmenes ---
    "resumen_diario": "resumen_diario",
    "resumen_semanal": "resumen_semanal",

    # --- Slots libres ---
    "slots_libres": "slots_libres",

    # --- Filtro por título ---
    "eventos_por_titulo": "Filtro de eventos por titulo",
    "Filtro de eventos por titulo": "Filtro de eventos por titulo",

    # (dejamos listos los demás por si luego los usas)
    "crear_evento": "crear_evento",
    "eliminar_evento": "eliminar_evento",
    "actualizar_evento": "actualizar_evento",
    "crear_evento_desde_texto": "Crear evento desde texto natural",
    "Crear evento desde texto natural": "Crear evento desde texto natural",
    "eventos_por_rango": "Eventos por rango",
    "Eventos por rango": "Eventos por rango",
    "eventos_todos_calendarios_rango": "Eventos de todos los calendarios por rango",
    "Eventos de todos los calendarios por rango": "Eventos de todos los calendarios por rango",
}


class MCPToolsClient:
    """
    Cliente MCP que:
    - Acepta nombres como llegan del frontend (corto/largo).
    - Inserta siempre context.user_id.
    - Llama a la tool del servidor con su nombre real.
    """
    def __init__(self, url: Optional[str] = None, user_id: Optional[str] = None):
        self.url = url or MCP_URL
        if not self.url:
            raise ValueError("MCP_URL no configurado. Define la variable de entorno MCP.")
        self.transport = StreamableHttpTransport(self.url)
        self.user_id = user_id or USUARIO_TEST
        if not self.user_id:
            raise ValueError("USUARIO_TEST no configurado. Define la variable de entorno USUARIO_TEST o pasa user_id.")

    async def _call_tool(self, tool_display_name: str, **kwargs) -> Any:
        """
        tool_display_name: como llega del frontend (corto o largo)
        kwargs: parámetros adicionales de la tool
        """
        # Normalizamos clave y resolvemos nombre real del servidor
        key = (tool_display_name or "").strip()
        server_tool_name = TOOLS_MAP.get(key, key)  # fallback: usar tal cual

        payload = {"context": {"user_id": self.user_id}}
        if kwargs:
            payload.update(kwargs)

        async with Client(transport=self.transport) as client:
            await client.ping()
            return await client.call_tool(server_tool_name, payload)

    # ---------- TOOLS SENCILLAS ----------

    async def listar_calendarios(self):
        # Acepta tanto alias corto como largo
        return await self._call_tool("Listar calendarios del usuario")

    async def resumen_diario(self, calendar_id: Optional[str] = None):
        # Si no se pasa calendar_id, usar "" -> todos los calendarios
        return await self._call_tool("resumen_diario", calendar_id=calendar_id or "")

    async def resumen_semanal(self, calendar_id: Optional[str] = None):
        return await self._call_tool("resumen_semanal", calendar_id=calendar_id or "")

    async def slots_libres(self, date: Optional[str] = None, duracion_minutos: int = 60,):
        # Si no manda fecha, usamos la de hoy en ISO
        date = date or _date.today().isoformat()
        
        return await self._call_tool(
            "slots_libres",
            date=date,
            duracion_minutos=duracion_minutos,
    )

    async def eventos_por_titulo(self, calendar_id: Optional[str] = None, keyword: str = ""):
        return await self._call_tool(
            "Filtro de eventos por titulo",
            calendar_id=calendar_id or "primary",
            keyword=keyword or "",
        )


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

        print("\n📌 Slots libres (hoy, 60 min)...")
        slots = await client.slots_libres(duracion_minutos=60)
        print(slots)

        print("\n📌 Eventos por título (keyword='reunión')...")
        eventos = await client.eventos_por_titulo(keyword="reunión")
        print(eventos)

    asyncio.run(main())
