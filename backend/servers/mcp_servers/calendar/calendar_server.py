# src/mcps/server/calendar_server.py
import os
import sys
import jwt
import pytz
import uvicorn
import json as _json
from pathlib import Path
from contextvars import ContextVar
from fastmcp import FastMCP, Context
from starlette.requests import Request
from fastmcp.tools.tool import ToolResult
from starlette.routing import Mount, Route
from starlette.middleware import Middleware
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from typing import Optional, List, Tuple, Dict
from starlette.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, time, timedelta
from starlette.middleware.base import BaseHTTPMiddleware, Request
# --- Fix Paths ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from utils.models import Event
from utils.time_helper import get_now
from sources.google_calendar import GoogleCalendarConnector
from sources.natural_parser import parse_natural_language_to_event
from utils.Keep_alive_mcp import keep_alive_mcp
from dotenv import load_dotenv

load_dotenv()

# Añadir la clave secreta de autenticación (Jarvis y MCP deben compartirla)
MCP_SECRET_KEY = os.getenv("MCP_SECRET_KEY")
# Asegúrate de que la clave secreta se cargó
if not MCP_SECRET_KEY:
    print("ADVERTENCIA: La clave secreta MCP_SECRET_KEY no está configurada.")
    
# Variable ahora con ContextVar para almacenar el contexto de la request actual
_current_request_context: ContextVar[dict] = ContextVar('mcp_context', default={})

# Middleware modificado para almacenar el contexto globalmente
class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware para validar JWT en requests al MCP Server"""
    
    def __init__(self, app, auth_secret: str):
        super().__init__(app)
        self.auth_secret = auth_secret
    
    async def dispatch(self, request: Request, call_next):
        
        # Permitir ping sin autenticación
        if request.url.path.endswith("/ping"):
            return await call_next(request)
        
        # Extraer el token del header Authorization
        auth_header = request.headers.get("Authorization", "")
        
        print(f"🔍 [Middleware] Path: {request.url.path}")
        print(f"🔍 [Middleware] Auth header: {auth_header[:50]}..." if auth_header else "No auth header")
        
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"},
                status_code=401
            )
        
        token = auth_header.replace("Bearer ", "")
        
        try:
            # Decodificar y validar el JWT
            payload = jwt.decode(token, self.auth_secret, algorithms=["HS256"])
            
            print(f" - [Middleware] JWT decodificado correctamente")
            print(f"   - user_id: {payload.get('sub')}")
            print(f"   - provider: {payload.get('provider')}")
            
            # Guardar en variable global
            mcp_context = {
                "user_id": payload.get("sub"), # sub (Subject): Es el identificador único del usuario (el "sujeto" del token). - User_id 
                "provider": payload.get("provider"),
                "google_access_token": payload.get("google_access_token"),
                "google_refresh_token": payload.get("google_refresh_token"),
            }
            
            _current_request_context.set(mcp_context)
            print(f"[Middleware] Context guardado globalmente: {mcp_context.get('user_id')}")
            
            response = await call_next(request)
            
            return response
            
        except jwt.ExpiredSignatureError:
            print(f"[Middleware] Token expirado")
            return JSONResponse(
                {"error": "Token expired"},
                status_code=401
            )
        except jwt.InvalidTokenError as e:
            print(f"[Middleware] Token inválido: {e}")
            return JSONResponse(
                {"error": f"Invalid token: {str(e)}"},
                status_code=401
            )

async def ping(request):
    return JSONResponse({"status": "ok", "service": "mcp-render"})

#mcp = CustomFastMCP(name="Google Calendar MCP", stateless_http=True)
mcp = FastMCP(name="Google Calendar MCP")  # Antes esta esto stateless_http=True

# Crear la app HTTP
mcp_app = mcp.http_app(path="/mcp")

# Aplicar middleware JWT personalizado
mcp_app_with_auth = Starlette(
    routes=[],
    middleware=[
        Middleware(JWTAuthMiddleware, auth_secret=MCP_SECRET_KEY)
    ]
)
mcp_app_with_auth.mount("/", mcp_app)

mcp_app_cors = CORSMiddleware(mcp_app_with_auth,
    allow_origins=[
        "https://mcp-nexus.vercel.app", 
        "https://inspector.use-mcp.dev", 
        "http://localhost:5173",
        "http://localhost:5000",
        "https://mcp-nexus.onrender.com",
        "https://gustavocoello.space",
        ],
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
    lifespan=mcp_app.lifespan
)

# Configuración del servidor MCP
#os.environ["DANGEROUSLY_OMIT_AUTH"] = "true"
#os.environ["MCP_SERVER_HOST"] = "0.0.0.0" 
#os.environ["MCP_SERVER_PORT"] = "3001"

def get_connector(context):
    user_id = context.get("user_id")
    access_token = context.get("google_access_token") 
    refresh_token = context.get("google_refresh_token")
    try:
        if not user_id or not access_token:
            raise ValueError("Falta user_id o access_token en el contexto")
        
        connector = GoogleCalendarConnector(
            user_id=user_id, 
            access_token=access_token, 
            refresh_token=refresh_token
            )
        
        # Ejecutamos la autenticación y capturamos los posibles nuevos tokens
        service, new_access_token, new_refresh_token = connector.authenticate()
        
        # Si hubo un refresh en Google, inyectamos los nuevos tokens al contexto
        # para que Jarvis los guarde.
        if new_access_token and new_access_token != access_token:
            context["google_new_access_token"] = new_access_token
        if new_refresh_token and new_refresh_token != refresh_token:
            context["google_new_refresh_token"] = new_refresh_token
            
        return connector
        
    except Exception as e:
        print(f"Error al obtener el conector de Google Calendar: {e}")
        raise
    
# =============== HELPER ================
def extract_context_from_fastmcp(context: Context) -> dict:
    """Extrae el contexto MCP desde la variable global inyectada por el middleware"""
    mcp_context = _current_request_context.get()
    
    print(f"[extract_context] Contexto: user_id={mcp_context.get('user_id')}, "
          f"has_token={bool(mcp_context.get('google_access_token'))}")
    
    if mcp_context:
        return mcp_context.copy()
    
    # Fallback: intentar desde request_context
    req_ctx = context.request_context
    mcp_context = {
        "user_id": getattr(req_ctx, "user_id", None),
        "provider": getattr(req_ctx, "provider", None),
        "google_access_token": getattr(req_ctx, "google_access_token", None),
        "google_refresh_token": getattr(req_ctx, "google_refresh_token", None),
    }
    
    print(f"[extract_context] Fallback - user_id={mcp_context.get('user_id')}, "
          f"has_token={bool(mcp_context.get('google_access_token'))}")
    
    return mcp_context

def _extract_id(value: str) -> str:
    """Sanitiza IDs — el LLM a veces manda el JSON completo como valor."""
    if not value:
        return value
    value = str(value).strip()
    if value.startswith("{"):
        try:
            parsed = _json.loads(value)
            return str(next(iter(parsed.values())))
        except Exception:
            pass
    return value

# =================================================================
#                         TOOLS DE GOOGLE CALENDAR
# =================================================================

# ───────────────────── FUNCIONES BÁSICAS ─────────────────────

@mcp.tool
async def crear_evento(context: Context, summary: str, description: str, start_time: str, end_time: str, calendar_id: str = "primary") -> dict:
    """
    crear_evento
    """
    calendar_id = _extract_id(calendar_id)
    mcp_context = extract_context_from_fastmcp(context)  
    gcal = get_connector(mcp_context)
    
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
async def google_resumen_diario(context: Context, calendar_id: Optional[str] = None) -> str:
    """
    google_resumen_diario
    """
    calendar_id = _extract_id(calendar_id) if calendar_id else None
    mcp_context = extract_context_from_fastmcp(context)  
    gcal = get_connector(mcp_context)
    return gcal.get_summary(calendar_id or None, range_type="daily")

@mcp.tool
async def google_resumen_semanal(context: Context, calendar_id: Optional[str] = None) -> str:
    """
    google_resumen_semanal
    """
    calendar_id = _extract_id(calendar_id) if calendar_id else None
    mcp_context = extract_context_from_fastmcp(context)  
    gcal = get_connector(mcp_context)
    return gcal.get_summary(calendar_id or None, range_type="weekly")


@mcp.tool(
    name="google_disponibilidad_diaria",
    description="Disponibilidad diaria: espacios libres entre eventos para una fecha dada en horario de Ecuador (GMT-5).",
)
async def google_disponibilidad_diaria(context: Context, date: Optional[str] = None, duration_minutes: int = 60):
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
            day = get_now().date()
    except Exception:
        return ToolResult(
            content=[{"type":"text","text":"Formato de fecha inválido. Usa YYYY-MM-DD."}],
            structured_content={"result": {}},
        )

    mcp_context = extract_context_from_fastmcp(context)  
    gcal = get_connector(mcp_context)
    res = gcal.get_free_slots(day, duration_minutes)  # dict con 'free_slots', 'busy_events'

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
async def google_disponibilidad_semanal(context: Context, duration_minutes: int = 60):
    if duration_minutes <= 0:
        return ToolResult(
            content=[{"type":"text","text":"La duración mínima debe ser mayor que 0."}],
            structured_content={"result": []},
        )

    mcp_context = extract_context_from_fastmcp(context)  
    gcal = get_connector(mcp_context)
    week = gcal.get_weekly_free_slots(duration_minutes=duration_minutes)  # lista de dicts con iso strings

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
async def google_listar_calendarios(context: Context) -> list:
    """
    Lista todos los calendarios disponibles del usuario.
    """
    mcp_context = extract_context_from_fastmcp(context)  
    gcal = get_connector(mcp_context)
    
    calendarios = gcal.list_calendars()
    return [
        {"id": c["id"], "name": c["name"]}
        for c in calendarios
    ]
    
@mcp.tool(
    name="eventos_por_titulo",
)
async def eventos_por_titulo(context: Context, calendar_id: str, keyword: str) -> list:
    """
    Devuelve eventos que contienen la palabra clave en el título.
    """
    calendar_id = _extract_id(calendar_id)
    keyword = _extract_id(keyword)
    mcp_context = extract_context_from_fastmcp(context)  
    gcal = get_connector(mcp_context)
    
    time_min = get_now().isoformat()
    return gcal.filter_events_by_title(calendar_id, keyword, time_min=time_min)

# ───────────────────── NLP → EVENT ─────────────────────
@mcp.tool(name="crear_evento_desde_texto")
async def crear_evento_desde_texto(context: Context, texto_usuario: str, calendar_id: str = None) -> dict:
    """
    Convierte texto en evento y lo crea en el calendario.
    """
    calendar_id = _extract_id(calendar_id)
    mcp_context = extract_context_from_fastmcp(context)  
    gcal = get_connector(mcp_context)

    event = parse_natural_language_to_event(texto_usuario)

    if not event:
        return {"error": "No se pudo parsear el evento"}

    calendar_id = calendar_id or "primary"
    creado = gcal.create_event(calendar_id, event)
    return {
        "mensaje": "Evento creado con éxito",
        "evento": creado
    }

@mcp.tool(name="eventos_por_rango")
async def eventos_por_rango(context: Context, calendar_id: str, start_date: str, end_date: str) -> list:
    """
    Recupera eventos de un calendario específico dentro de un rango de fechas.
    """
    calendar_id = _extract_id(calendar_id)
    mcp_context = extract_context_from_fastmcp(context)  
    gcal = get_connector(mcp_context)

    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    events = gcal.get_events_by_range(calendar_id, start, end)
    return [event.dict() for event in events]


@mcp.tool(name="eventos_todos_calendarios_rango")
async def eventos_todos_calendarios_rango(context: Context, start_date: str, end_date: str) -> list:
    """
    Recupera eventos de todos los calendarios del usuario en un rango de fechas.
    """
    mcp_context = extract_context_from_fastmcp(context)  
    gcal = get_connector(mcp_context)
    
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    events = gcal.fetch_events_by_range(start, end)
    return [event.dict() for event in events]

# ---------------- ACTUALIZAR Y ELIMINAR EVENTOS ----------------

@mcp.tool(name="actualizar_evento")
async def actualizar_evento(context: Context, calendar_id: str, event_id: str, summary: Optional[str] = None, description: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None) -> dict:
    """Actualiza un evento existente. Solo modifica los campos que se pasen."""
    calendar_id = _extract_id(calendar_id)
    mcp_context = extract_context_from_fastmcp(context)
    gcal = get_connector(mcp_context)
    return gcal.update_event(calendar_id, event_id, 
                             summary=summary, description=description,
                             start_time=start_time, end_time=end_time)

@mcp.tool(name="eliminar_evento")
async def eliminar_evento(context: Context, calendar_id: str, event_id: str) -> dict:
    """Elimina un evento del calendario por su ID."""
    calendar_id = _extract_id(calendar_id)
    mcp_context = extract_context_from_fastmcp(context)
    gcal = get_connector(mcp_context)
    return gcal.delete_event(calendar_id, event_id)


#""" # Para utilizarlo en local
if __name__ == "__main__":
        keep_alive_mcp()
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8001,
            )
#"""       