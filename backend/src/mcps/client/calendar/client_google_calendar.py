# src/mcps/client/calendar/client_google_calendar.py
from typing import Optional, Dict, List, Any
from ..base_client import BaseMCPClient

class CalendarMCPClient(BaseMCPClient):
    """
    Cliente MCP especializado para Google Calendar.
    Hereda la lógica de seguridad (JWT) y transporte de BaseMCPClient.
    """

    def __init__(self, url: Optional[str] = None, user_id: Optional[str] = None):
        # El provider "google_calendar" le dice a la base qué token generar
        super().__init__(
            url=url, 
            provider="google_calendar", 
            user_id=user_id
        )

    # ---------- TOOLS SENCILLAS ----------

    async def google_listar_calendarios(self):
        # Acepta tanto alias corto como largo
        result = await self._call_server("google_listar_calendarios", {})
        return {
            "prompt": "This is a MCP Tools response to google calendar information.",
            "data": result.content or [],
        }
        

    async def google_resumen_diario(self, calendar_id: Optional[str] = None):
        # Si no se pasa calendar_id, usar "" -> todos los calendarios
        result = await self._call_server("google_resumen_diario", calendar_id=calendar_id or "")
        return {
            "prompt": "This is a MCP Tools response to google calendar information.",
            "data": result.content or [],
        }

    async def google_resumen_semanal(self, calendar_id: Optional[str] = None):
        result = await self._call_server("google_resumen_semanal", calendar_id=calendar_id or "")
        return {
            "prompt": "This is a MCP Tools response to google calendar information.",
            "data": result.content or [],
        }

    async def google_disponibilidad_diaria(self, date: Optional[str] = None, duration_minutes: int = 60):
        args = {"duration_minutes": duration_minutes}
        if date:
            args["date"] = date

        # Llamas la tool por su nombre exacto
        result = await self._call_server("google_disponibilidad_diaria", **args)
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

        result = await self._call_server("google_disponibilidad_semanal", **args)

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

