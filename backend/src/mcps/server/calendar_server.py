# src/mcps/server/calendar_server.py
import os
import sys
import anyio
from pathlib import Path
from fastmcp import FastMCP, Context

from datetime import datetime, timezone

# --- Fix Paths ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.mcps.sources.calendar.google_calendar import GoogleCalendarConnector
from src.mcps.sources.calendar.natural_parser import parse_natural_language_to_event
#from src.mcps.server.fastmcp import FastMCP as CustomFastMCP
from src.mcps.core.models import Event

flask_app = None  

def set_flask_app(app):
    global flask_app
    flask_app = app

#mcp = CustomFastMCP(name="Google Calendar MCP", stateless_http=True)
mcp = FastMCP(name="Google Calendar MCP")


# Configuración del servidor MCP
#os.environ["DANGEROUSLY_OMIT_AUTH"] = "true"
#os.environ["MCP_SERVER_HOST"] = "0.0.0.0" 
#os.environ["MCP_SERVER_PORT"] = "3001"

def get_connector(context):
    user_id = context.get("user_id")
    if not user_id:
        raise ValueError("Falta user_id en el contexto")
    return GoogleCalendarConnector(user_id=user_id)


# ───────────────────── FUNCIONES BÁSICAS ─────────────────────

@mcp.tool
async def crear_evento(context: dict, summary: str, description: str, start_time: str, end_time: str, calendar_id: str = "primary") -> dict:
    """
    Crea un nuevo evento.
    """
    gcal = get_connector(context)
    event = Event(
        title=summary,
        description=description,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        source="google_calendar"
    )
    return gcal.create_event(calendar_id, event)

@mcp.tool
async def eliminar_evento(context: dict, calendar_id: str, event_id: str) -> bool:
    """
    Elimina un evento.
    """
    gcal = get_connector(context)
    return gcal.delete_event(calendar_id, event_id)

@mcp.tool
async def actualizar_evento(context: dict, calendar_id: str, event_id: str, summary: str = None, description: str = None) -> dict:
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

@mcp.tool
async def resumen_diario(context: dict, calendar_id: str) -> str:
    """
    Resumen diario de todos los calendarios o calendario seleccionado.
    """
    gcal = get_connector(context)
    return gcal.get_summary(calendar_id or None, range_type="daily")

@mcp.tool
async def resumen_semanal(context: dict, calendar_id: str) -> str:
    """
    Resumen semanal de todos los calendarios o calendario seleccionado.
    """
    gcal = get_connector(context)
    return gcal.get_summary(calendar_id or None, range_type="weekly")

@mcp.tool
async def slots_libres(context: dict, calendar_id: str, date: str, duracion_minutos: int = 60) -> list:
    """
    Buscan lugares libres en un día.
    """
    gcal = get_connector(context)
    fecha = datetime.fromisoformat(date).date()
    slots = gcal.get_free_slots(calendar_id, fecha, duracion_minutos)
    return [f"{s[0].isoformat()} — {s[1].isoformat()}" for s in slots]

@mcp.tool(
    name="Filtro de eventos por titulo"
)
async def eventos_por_titulo(context: dict, calendar_id: str, keyword: str) -> list:
    """
    Devuelve eventos que contienen la palabra clave en el título.
    """
    gcal = get_connector(context)
    
    time_min = datetime.now(timezone.utc).isoformat()
    return gcal.filter_events_by_title(calendar_id, keyword, time_min=time_min)

@mcp.tool(name="Listar calendarios del usuario")
async def listar_calendarios(context: dict) -> list:
    """
    Lista todos los calendarios disponibles del usuario.
    """
    gcal = get_connector(context)
    calendarios = gcal.list_calendars()
    return [
        {"id": c["id"], "nombre": c["name"]}
        for c in calendarios
    ]
# ───────────────────── NLP → EVENT ─────────────────────
@mcp.tool(name="Crear evento desde texto natural")
async def crear_evento_desde_texto(context: dict, texto_usuario: str, calendar_id: str = None) -> dict:
    """
    Convierte texto en evento y lo crea en el calendario.
    """
    gcal = get_connector(context)
    event = parse_natural_language_to_event(texto_usuario)

    if not event:
        return {"error": "No se pudo parsear el evento"}

    calendar_id = calendar_id or context.get("calendar_id", "primary")
    creado = gcal.create_event(calendar_id, event)
    return {
        "mensaje": "Evento creado con éxito",
        "evento": creado
    }

@mcp.tool(name="Eventos por rango")
async def eventos_por_rango(context: dict, calendar_id: str, start_date: str, end_date: str) -> list:
    """
    Recupera eventos de un calendario específico dentro de un rango de fechas.
    """
    gcal = get_connector(context)
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    events = gcal.get_events_by_range(calendar_id, start, end)
    return [event.dict() for event in events]


@mcp.tool(name="Eventos de todos los calendarios por rango")
async def eventos_todos_calendarios_rango(context: dict, start_date: str, end_date: str) -> list:
    """
    Recupera eventos de todos los calendarios del usuario en un rango de fechas.
    """
    gcal = get_connector(context)
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    events = gcal.fetch_events_by_range(start, end)
    return [event.dict() for event in events]



#print(tool_with_log.__name__)

def debug_list_tools():
    tools = anyio.run(lambda: mcp._tool_manager.list_tools())
    print("🧰 Herramientas en ToolManager:", [t.name for t in tools])

debug_list_tools()
#""" # Para utilizarlo en local
if __name__ == "__main__":
    from app import app as flask_app
    set_flask_app(flask_app)
    with flask_app.app_context():
        mcp.run(
            transport="http",
            host="0.0.0.0",
            port=8000
        )
#"""       