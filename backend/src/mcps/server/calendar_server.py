# src/mcps/server/calendar/server
from mcp import Tool
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from datetime import datetime
import sys
import os

from pathlib import Path

# --- Fix Paths ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.mcps.sources.calendar.google_calendar import GoogleCalendarConnector
from src.mcps.sources.calendar.natural_parser import parse_natural_language_to_event
from src.mcps.core.models import Event
from app import app

mcp = FastMCP(name="Google Calendar MCP", stateless_http=True)

original_tool_decorator = mcp.tool

def tool_with_log(*args, **kwargs):
    def wrapper(func):
        print(f"✔️ Registrada herramienta: {func.__name__}")
        return original_tool_decorator(*args, **kwargs)(func)
    return wrapper

mcp.tool = tool_with_log

# Configuración del servidor MCP
os.environ["DANGEROUSLY_OMIT_AUTH"] = "true"
os.environ["MCP_SERVER_HOST"] = "0.0.0.0"
os.environ["MCP_SERVER_PORT"] = "3001"

def get_connector(context):
    user_id = context.get("user_id")
    if not user_id:
        raise ValueError("Falta user_id en el contexto")
    return GoogleCalendarConnector(user_id=user_id)


# ───────────────────── FUNCIONES BÁSICAS ─────────────────────

@mcp.tool()
def crear_evento(context: dict, summary: str, description: str, start_time: str, end_time: str, calendar_id: str = "primary") -> dict:
    gcal = get_connector(context)
    event = Event(
        title=summary,
        description=description,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        source="google_calendar"
    )
    return gcal.create_event(calendar_id, event)

@mcp.tool()
def eliminar_evento(context: dict, calendar_id: str, event_id: str) -> bool:
    gcal = get_connector(context)
    return gcal.delete_event(calendar_id, event_id)

@mcp.tool()
def actualizar_evento(context: dict, calendar_id: str, event_id: str, summary: str = None, description: str = None) -> dict:
    """
    Actualiza campos básicos (título y descripción) de un evento.
    """
    gcal = get_connector(context)
    
    cambios = {}
    if summary:
        cambios["summary"] = summary
    if description:
        cambios["description"] = description

    if not cambios:
        return {"error": "No se proporcionaron campos a actualizar"}

    return gcal.update_event(calendar_id, event_id, cambios)

# ───────────────────── INFORMACIÓN ─────────────────────

@mcp.tool()
def resumen_diario(context: dict, calendar_id: str) -> str:
    gcal = get_connector(context)
    return gcal.get_summary(calendar_id or None, range_type="daily")

@mcp.tool()
def resumen_semanal(context: dict, calendar_id: str) -> str:
    gcal = get_connector(context)
    return gcal.get_summary(calendar_id or None, range_type="weekly")

@mcp.tool()
def slots_libres(context: dict, calendar_id: str, date: str, duracion_minutos: int = 60) -> list:
    gcal = get_connector(context)
    fecha = datetime.fromisoformat(date).date()
    slots = gcal.get_free_slots(calendar_id, fecha, duracion_minutos)
    return [f"{s[0].isoformat()} — {s[1].isoformat()}" for s in slots]

@mcp.tool()
def eventos_por_titulo(context: dict, calendar_id: str, keyword: str) -> list:
    """
    Devuelve eventos que contienen la palabra clave en el título.
    """
    gcal = get_connector(context)
    
    time_min = datetime.now().isoformat()
    return gcal.filter_events_by_title(calendar_id, keyword, time_min=time_min)

# ───────────────────── NLP → EVENT ─────────────────────

@mcp.tool()
def parsear_evento_desde_texto(texto_usuario: str) -> dict:
    """
    Transforma texto natural en un evento estructurado.
    """    
    event = parse_natural_language_to_event(texto_usuario)
    if not event:
        return {"error": "No se pudo parsear el evento"}
    return {
        "title": event.title,
        "start_time": event.start_time.isoformat(),
        "end_time": event.end_time.isoformat(),
        "description": event.description
    }

""" # Para utilizarlo en local
if __name__ == "__main__":
    print(tool_with_log.__name__)
    
    with app.app_context():
        mcp.run(
            transport="streamable-http",
        )
"""       