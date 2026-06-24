import json
from typing import Optional, Dict, List
from langchain_core.tools import tool, Tool
from .helpers import _clean_id, _parse_args, _parse_mcp_result, _run
from src.services.mcps.client.client_manager import MCPClientManager
from src.services.agent.common.helpers import mcp_offline_error, mcp_no_client


# Base de datos y Chat 
from src.database.models.models import Message

# --- CALENDAR TOOLS ---
def build_calendar_tools(user_id: str, chat_id: Optional[str] = None, db_session=None, client_type: str = "web"):
    """
    Factory: genera las 12 tools de Google Calendar vinculadas a un user_id.
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "google_calendar"

    def get_calendar():
        return manager.get_client(provider_name)
    
    def _record_tool_usage(tool_name: str):
        """Guarda un registro ligero en BD de qué herramienta usó el agente."""
        if not db_session or not chat_id:
            return
        
        # 1. Guardar en la Base de Datos (rol: mcp-tool)
        # Solo guardamos el nombre de la herramienta. ¡Nada de JSONs gigantes!
        mcp_context_str = json.dumps({
            "tool_used": tool_name,
            "provider": provider_name
        })
        
        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context_str)
        db_session.add(mcp_msg)
        db_session.commit()
    
    @tool
    def google_listar_calendarios() -> str:
        """Lista todos los calendarios del usuario en Google Calendar."""
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
            result = _run(client.google_listar_calendarios())
            _record_tool_usage("google_listar_calendarios")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "google_listar_calendarios", str(e))

    @tool
    def google_resumen_diario(calendar_id: str = "") -> str:
        """
        Resumen de eventos de hoy. 
        Usa calendar_id="" para todos los calendarios.
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")

            result = _run(client.google_resumen_diario(calendar_id=calendar_id or None))
            _record_tool_usage("google_resumen_diario")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "google_resumen_diario", str(e))

    @tool
    def google_resumen_semanal(calendar_id: str = "") -> str:
        """
        Resumen de eventos de la semana actual.
        Usa calendar_id="" para todos los calendarios.
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")

            result = _run(client.google_resumen_semanal(calendar_id=calendar_id or None))
            _record_tool_usage("google_resumen_semanal")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "google_resumen_semanal", str(e))

    @tool
    def google_disponibilidad_diaria(date: str = "", duration_minutes: int = 60) -> str:
        """
        Espacios libres del día en horario Ecuador (GMT-5).
        Input: date (YYYY-MM-DD, vacío = hoy), duration_minutes (mínimo en minutos).
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
            result = _run(client.google_disponibilidad_diaria(
                date=date or None, duration_minutes=duration_minutes
            ))
            _record_tool_usage("google_disponibilidad_diaria")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "google_disponibilidad_diaria", str(e))

    @tool
    def google_disponibilidad_semanal(duration_minutes: int = 60) -> str:
        """Espacios libres de los próximos 7 días en horario Ecuador (GMT-5)."""
        try:
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")

            result = _run(client.google_disponibilidad_semanal(duration_minutes=duration_minutes))
            _record_tool_usage("google_disponibilidad_semanal")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "google_disponibilidad_semanal", str(e))

    @tool
    def eventos_por_titulo(calendar_id: str, keyword: Optional[str] = None) -> str:
        """
        Busca eventos que contengan una palabra clave en el título.
        Input: calendar_id, keyword.
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
            args = _parse_args(
                {"calendar_id": calendar_id, "keyword": keyword},
                ["calendar_id", "keyword"]
            )
            calendar_id = _clean_id(args.get("calendar_id", calendar_id))
            keyword = args.get("keyword", keyword)
            
            result = _run(client.eventos_por_titulo(calendar_id=calendar_id, keyword=keyword))
            _record_tool_usage("eventos_por_titulo")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "eventos_por_titulo", str(e))

    @tool
    def eventos_por_rango(calendar_id: str, start_date: str, end_date: Optional[str] = None) -> str:
        """
        Eventos de un calendario en un rango de fechas.
        Input: calendar_id, start_date (ISO), end_date (ISO).
        """
        try:
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")

            args = _parse_args(
                {"calendar_id": calendar_id, "start_date": start_date, "end_date": end_date or ""},
                ["calendar_id", "start_date", "end_date"]
            )
            calendar_id = _clean_id(args.get("calendar_id", calendar_id))
            start_date = args.get("start_date", start_date)
            end_date = args.get("end_date", end_date)

            if not end_date:
                return "Error: end_date es requerido."

            result = _run(client.eventos_por_rango(
                calendar_id=calendar_id, start_date=start_date, end_date=end_date
            ))
            _record_tool_usage("eventos_por_rango")
            return _parse_mcp_result(result)
        except Exception as e:
                return mcp_offline_error("Google Calendar", "eventos_por_rango", str(e))

    @tool
    def eventos_todos_calendarios_rango(start_date: str, end_date: Optional[str] = None) -> str:
        """
        Eventos de TODOS los calendarios en un rango de fechas.
        Input: start_date (ISO), end_date (ISO).
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
            args = _parse_args(
                {"start_date": start_date, "end_date": end_date or ""},
                ["start_date", "end_date"]
            )
            start_date = args.get("start_date", start_date)
            end_date = args.get("end_date", end_date)
            
            if not end_date:
                return "Error: end_date es requerido."
        
            result = _run(get_calendar().eventos_todos_calendarios_rango(
                start_date=start_date, end_date=end_date
            ))
            _record_tool_usage("eventos_todos_calendarios_rango")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "eventos_todos_calendarios_rango", str(e))

    @tool
    def crear_evento(summary: str, description: str = "", start_time: Optional[str] = None,
                     end_time: Optional[str] = None, calendar_id: str = "primary") -> str:
        """
        Crea un evento en Google Calendar.
        Input: summary, description, start_time (ISO), end_time (ISO), calendar_id.
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
            safe_description = description or ""
            
            args = _parse_args(
                {
                    "summary": summary, 
                    "description": safe_description,
                    "start_time": start_time or "", 
                    "end_time": end_time or "", 
                    "calendar_id": calendar_id
                },
                ["summary", "start_time", "end_time"]
            )
            summary = args.get("summary", summary)
            description = args.get("description", safe_description)
            start_time = args.get("start_time", start_time)
            end_time = args.get("end_time", end_time)
            calendar_id = _clean_id(args.get("calendar_id", calendar_id))

            # Validación manual (tú tienes el control, no Pydantic)
            if not summary or not start_time or not end_time:
                return "Error: summary, start_time y end_time son requeridos."
            
            result = _run(get_calendar().crear_evento(
                summary=summary, description=description,
                start_time=start_time, end_time=end_time, calendar_id=calendar_id
            ))
            _record_tool_usage("crear_evento")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "crear_evento", str(e))

    @tool
    def crear_evento_desde_texto(texto_usuario: str, calendar_id: str = "primary") -> str:
        """
        Crea un evento a partir de lenguaje natural.
        Ejemplo: "Reunión con Juan el martes a las 3pm por 1 hora".
        Input: texto_usuario, calendar_id (opcional).
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
            result = _run(get_calendar().crear_evento_desde_texto(
                texto_usuario=texto_usuario, calendar_id=calendar_id
            ))
            _record_tool_usage("crear_evento_desde_texto")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "crear_evento_desde_texto", str(e))

    @tool
    def actualizar_evento(calendar_id: str, event_id: str, summary: str = "",
                          description: str = "", start_time: str = "", end_time: str = "") -> str:
        """
        Actualiza un evento existente. Solo modifica los campos que se pasen.
        Input: calendar_id, event_id (obtenido de búsqueda previa), 
               y los campos a cambiar: summary, description, start_time, end_time.
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
            args = _parse_args(
                {"calendar_id": calendar_id, "event_id": event_id,
                "summary": summary, "description": description,
                "start_time": start_time, "end_time": end_time},
                ["calendar_id", "event_id"]
            )
            calendar_id = _clean_id(args.get("calendar_id", calendar_id))
            event_id = _clean_id(args.get("event_id", event_id))
            summary = args.get("summary", summary)
            description = args.get("description", description)
            start_time = args.get("start_time", start_time)
            end_time = args.get("end_time", end_time)
            
            result = _run(get_calendar().actualizar_evento(
                calendar_id=calendar_id, event_id=event_id,
                summary=summary or None, description=description or None,
                start_time=start_time or None, end_time=end_time or None
            ))
            _record_tool_usage("actualizar_evento")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "actualizar_evento", str(e))

    @tool
    def eliminar_evento(calendar_id: str, event_id: str) -> str:
        """
        Elimina un evento del calendario.
        SOLO usar cuando el usuario lo pida explícitamente.
        Input: calendar_id, event_id (obtenido de búsqueda previa).
        """
        try: 
            client = get_calendar()
            if not client:
                return mcp_no_client("Google Calendar")
        
            args = _parse_args(
                {"calendar_id": calendar_id, "event_id": event_id},
                ["calendar_id", "event_id"]
            )
            calendar_id = _clean_id(args.get("calendar_id", calendar_id))
            event_id = _clean_id(args.get("event_id", event_id))
            
            result = _run(get_calendar().eliminar_evento(
                calendar_id=calendar_id, event_id=event_id
            ))
            _record_tool_usage("eliminar_evento")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Google Calendar", "eliminar_evento", str(e))

    return [
        google_listar_calendarios,
        google_resumen_diario,
        google_resumen_semanal,
        google_disponibilidad_diaria,
        google_disponibilidad_semanal,
        eventos_por_titulo,
        eventos_por_rango,
        eventos_todos_calendarios_rango,
        crear_evento,
        crear_evento_desde_texto,
        actualizar_evento,
        eliminar_evento,
    ]