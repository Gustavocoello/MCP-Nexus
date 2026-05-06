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
        super().__init__(url=url, provider="google_calendar", user_id=user_id)

    # --- CALENDARIOS ---

    async def google_listar_calendarios(self):
        result = await self._call_server("google_listar_calendarios", {})
        return {"data": result.content or [], "success": not result.is_error}

    # --- RESÚMENES ---

    async def google_resumen_diario(self, calendar_id: Optional[str] = None):
        result = await self._call_server("google_resumen_diario", {"calendar_id": calendar_id or ""})
        return {"data": result.content or [], "success": not result.is_error}

    async def google_resumen_semanal(self, calendar_id: Optional[str] = None):
        result = await self._call_server("google_resumen_semanal", {"calendar_id": calendar_id or ""})
        return {"data": result.content or [], "success": not result.is_error}

    # --- DISPONIBILIDAD ---

    async def google_disponibilidad_diaria(self, date: Optional[str] = None, duration_minutes: int = 60):
        args = {"duration_minutes": duration_minutes}
        if date:
            args["date"] = date
        result = await self._call_server("google_disponibilidad_diaria", args)

        content_blocks = []
        if result.content:
            for cb in result.content:
                content_blocks.append(cb.text if hasattr(cb, "text") else str(cb))
        structured = result.structured_content.get("result", []) if result.structured_content else []

        return {"success": not result.is_error, "lines": content_blocks, "slots": structured}

    async def google_disponibilidad_semanal(self, duration_minutes: int = 60):
        result = await self._call_server("google_disponibilidad_semanal", {"duration_minutes": duration_minutes})

        content_blocks = []
        if result.content:
            for cb in result.content:
                content_blocks.append(cb.text if hasattr(cb, "text") else str(cb))
        structured = result.structured_content.get("result", []) if result.structured_content else []

        return {"success": not result.is_error, "lines": content_blocks, "weekly": structured}

    # --- EVENTOS: LECTURA ---

    async def eventos_por_titulo(self, calendar_id: str, keyword: str):
        result = await self._call_server("eventos_por_titulo", {
            "calendar_id": calendar_id,
            "keyword": keyword
        })
        return {"data": result.content or [], "success": not result.is_error}

    async def eventos_por_rango(self, calendar_id: str, start_date: str, end_date: str):
        result = await self._call_server("eventos_por_rango", {
            "calendar_id": calendar_id,
            "start_date": start_date,
            "end_date": end_date
        })
        return {"data": result.content or [], "success": not result.is_error}

    async def eventos_todos_calendarios_rango(self, start_date: str, end_date: str):
        result = await self._call_server("eventos_todos_calendarios_rango", {
            "start_date": start_date,
            "end_date": end_date
        })
        return {"data": result.content or [], "success": not result.is_error}

    # --- EVENTOS: ESCRITURA ---

    async def crear_evento(self, summary: str, description: str, start_time: str,
                           end_time: str, calendar_id: str = "primary"):
        result = await self._call_server("crear_evento", {
            "summary": summary,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "calendar_id": calendar_id
        })
        return {"data": result.content or [], "success": not result.is_error}

    async def crear_evento_desde_texto(self, texto_usuario: str, calendar_id: str = None):
        args = {"texto_usuario": texto_usuario}
        if calendar_id:
            args["calendar_id"] = calendar_id
        result = await self._call_server("crear_evento_desde_texto", args)
        return {"data": result.content or [], "success": not result.is_error}

    async def actualizar_evento(self, calendar_id: str, event_id: str,
                                summary: str = None, description: str = None,
                                start_time: str = None, end_time: str = None):
        args = {"calendar_id": calendar_id, "event_id": event_id}
        if summary:     args["summary"] = summary
        if description: args["description"] = description
        if start_time:  args["start_time"] = start_time
        if end_time:    args["end_time"] = end_time
        result = await self._call_server("actualizar_evento", args)
        return {"data": result.content or [], "success": not result.is_error}

    async def eliminar_evento(self, calendar_id: str, event_id: str):
        result = await self._call_server("eliminar_evento", {
            "calendar_id": calendar_id,
            "event_id": event_id
        })
        return {"data": result.content or [], "success": not result.is_error}

