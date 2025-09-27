# src/mcps/server/calendar_server.py
import os
import sys
import pytz
import anyio
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from fastmcp import FastMCP, Context
from fastmcp.tools.tool import ToolResult
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.wsgi import WSGIMiddleware
from starlette.responses import JSONResponse
from datetime import datetime, timezone, time, timedelta

# --- Fix Paths ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.mcps.sources.calendar.google_calendar import GoogleCalendarConnector
from src.mcps.sources.calendar.natural_parser import parse_natural_language_to_event
#from src.mcps.server.fastmcp import FastMCP as CustomFastMCP
from src.services.auth.keep_alive import keep_alive
from src.mcps.core.models import Event
from app import app as flask_app

async def ping(request):
    return JSONResponse({"status": "ok", "service": "mcp-render"})

#mcp = CustomFastMCP(name="Google Calendar MCP", stateless_http=True)
mcp = FastMCP(name="Google Calendar MCP")  # Antes esta esto stateless_http=True

mcp_app = mcp.http_app(path="/mcp")

mcp_app_cors = CORSMiddleware(mcp_app,
    allow_origins=[
        "http://localhost:3000", 
        "https://inspector.use-mcp.dev", 
        "http://localhost:5173", 
        "https://mcp-nexus.vercel.app", 
        "https://mcp-nexus-gustavo-coellos-projects.vercel.app" 
        ] ,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["mcp-session-id"]
)
# Envolviendo con CORS globalmente
app = Starlette(
    routes=[
        Mount("/mcp-server", app=mcp_app_cors),
        Route("/ping", ping)
    ], 
    lifespan=mcp_app.lifespan)

app.mount("/", WSGIMiddleware(flask_app))
# Configuración del servidor MCP
#os.environ["DANGEROUSLY_OMIT_AUTH"] = "true"
#os.environ["MCP_SERVER_HOST"] = "0.0.0.0" 
#os.environ["MCP_SERVER_PORT"] = "3001"

def get_connector(context):
    user_id = context.get("user_id")
    try:
        if not user_id:
            raise ValueError("Falta user_id en el contexto")
        connector = GoogleCalendarConnector(user_id=user_id)
        connector.authenticate()
        return connector
    except Exception as e:
        print(f"Error al obtener el conector de Google Calendar: {e}")
        raise
    
    
# Zona horaria de Ecuador (GMT-5)
EC_TZ = pytz.timezone("America/Guayaquil")

def ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return EC_TZ.localize(dt)
    return dt.astimezone(EC_TZ)

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

# ───────────────────── INFORMACIÓN ─────────────────────

@mcp.tool
async def google_resumen_diario(context: dict, calendar_id: Optional[str] = None) -> str:
    """
    Resumen diario de todos los calendarios o calendario seleccionado.
    """
    gcal = get_connector(context)
    return gcal.get_summary(calendar_id or None, range_type="daily")

@mcp.tool
async def google_resumen_semanal(context: dict, calendar_id: Optional[str] = None) -> str:
    """
    Resumen semanal de todos los calendarios o calendario seleccionado.
    """
    gcal = get_connector(context)
    return gcal.get_summary(calendar_id or None, range_type="weekly")


@mcp.tool(
    name="google_disponibilidad_diaria",
    description="Disponibilidad diaria: espacios libres entre eventos para una fecha dada en horario de Ecuador (GMT-5).",
)
async def google_disponibilidad_diaria(
    context: dict,
    date: Optional[str] = None,
    duration_minutes: int = 60
):
    # Validaciones
    if duration_minutes <= 0:
        return ToolResult(
            content=[{"type":"text","text":"La duración mínima debe ser mayor que 0."}],
            structured_content={"result": {}},
        )

    # Parse fecha
    try:
        if date:
            day = datetime.fromisoformat(date).date()
        else:
            day = datetime.now(EC_TZ).date()
    except Exception:
        return ToolResult(
            content=[{"type":"text","text":"Formato de fecha inválido. Usa YYYY-MM-DD."}],
            structured_content={"result": {}},
        )

    g = get_connector(context)
    res = g.get_free_slots(day, duration_minutes)  # dict con 'free_slots', 'busy_events'

    # Formato humano
    if not res["free_slots"]:
        content = [{"type":"text","text":"No hay espacios disponibles para esa fecha."}]
    else:
        lines = [f"Espacios disponibles para el día {day.isoformat()}:"]
        for i, (s, e) in enumerate(res["free_slots"], start=1):
            # s, e ya son datetime aware en EC
            lines.append(f"{i}. {s.strftime('%H:%M')} - {e.strftime('%H:%M')} EC (GMT-5)")
        content = [{"type":"text","text": line} for line in lines]

    # structured_content
    structured = {
        "date": day.isoformat(),
        "free_slots": [
            {"start": s.isoformat(), "end": e.isoformat()}
            for (s, e) in res["free_slots"]
        ],
        "busy_events": [
            {
                "start": be["start"].isoformat(),
                "end": be["end"].isoformat(),
                "summary": be.get("summary", ""),
                "calendar_id": be.get("calendar_id"),
                "all_day": be.get("all_day", False)
            }
            for be in res["busy_events"]
        ]
    }

    return ToolResult(
        content=content,
        structured_content={"result": structured},
    )



@mcp.tool(
    name="google_disponibilidad_semanal",
    description="Disponibilidad semanal: espacios libres para los próximos 7 días en horario de Ecuador (GMT-5).",
)

async def google_disponibilidad_semanal(context: dict, duration_minutes: int = 60):
    if duration_minutes <= 0:
        return ToolResult(
            content=[{"type":"text","text":"La duración mínima debe ser mayor que 0."}],
            structured_content={"result": []},
        )

    g = get_connector(context)
    week = g.get_weekly_free_slots(duration_minutes=duration_minutes)  # lista de dicts con iso strings

    content_lines = ["Disponibilidad para los próximos 7 días:"]
    for day_entry in week:
        date = day_entry["date"]
        free_slots = day_entry.get("free_slots", [])
        if free_slots:
            for fs in free_slots:
                # fs["start"] y fs["end"] son strings ISO con offset -05:00
                hora_inicio = fs["start"][11:16]
                hora_fin = fs["end"][11:16]
                content_lines.append(f"Día {date}: {hora_inicio} - {hora_fin} EC (GMT-5)")
        else:
            content_lines.append(f"Día {date}: sin espacios disponibles")

    content = [{"type":"text","text": line} for line in content_lines]

    return ToolResult(
        content=content,
        structured_content={"result": week},
    )
@mcp.tool()
async def google_listar_calendarios(context: dict) -> list:
    """
    Lista todos los calendarios disponibles del usuario.
    """
    gcal = get_connector(context)
    calendarios = gcal.list_calendars()
    return [
        {"id": c["id"], "name": c["name"]}
        for c in calendarios
    ]
    
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
        import uvicorn
        from app import app as flask_app
        with flask_app.app_context():
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=8000,
            )
#"""       