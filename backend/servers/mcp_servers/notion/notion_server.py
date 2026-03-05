# src/mcps/server/notion_server.py
import os
import sys
import jwt
import pytz
import uvicorn
from pathlib import Path
from fastmcp import FastMCP, Context
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, Request
from contextvars import ContextVar
from dotenv import load_dotenv
from typing import Optional, Dict, List
from sources.notion_connector import NotionConnector

# --- Tu Helper de Tiempo ---

current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from mcp_servers.utils.time_helper import get_now
from utils.Keep_alive_mcp import keep_alive_mcp

load_dotenv()

# Añadir la clave secreta de autenticación (Jarvis y MCP deben compartirla)
MCP_SECRET_KEY = os.getenv("MCP_SECRET_KEY")
# Asegúrate de que la clave secreta se cargó
if not MCP_SECRET_KEY:
    print("ADVERTENCIA: La clave secreta MCP_SECRET_KEY no está configurada.")

# Contexto para JWT
_current_request_context: ContextVar[dict] = ContextVar('notion_mcp_context', default={})

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
            print(f" - user_id: {payload.get('user_id') or payload.get('sub')}")
            print(f" - provider: {payload.get('provider')}")
            
            # Guardar en variable global
            mcp_context = {
                "user_id": payload.get("user_id") or payload.get("sub"),
                "provider": payload.get("provider"),
                "notion_api_key": payload.get("notion_api_key"), # Extraído del JWT del backend
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

# Instancia de FastMCP
mcp = FastMCP(name="Notion MCP Server")

# Configuración de la App Starlette (Igual a tu Calendar)
mcp_app = mcp.http_app(path="/mcp")

# Aplicar el middleware de autenticación a la app del MCP
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
        Route("/ping", lambda r: JSONResponse({"status": "ok", "service": "notion-mcp"}))
    ], 
    lifespan=mcp_app.lifespan
)

#==================== HELPERS =====================
def extract_context_from_fastmcp(context: Context) -> dict:
    """Extrae el contexto MCP desde la variable global o el fallback de FastMCP"""
    mcp_context = _current_request_context.get()
    
    print(f" [extract_context] Contexto Global: user_id={mcp_context.get('user_id')}, "
          f"has_notion_token={bool(mcp_context.get('notion_api_key'))}")
    
    if mcp_context and mcp_context.get('notion_api_key'):
        return mcp_context.copy()
    
    # Fallback: intentar desde request_context (Igual que en Calendar)
    req_ctx = context.request_context
    mcp_context = {
        "user_id": getattr(req_ctx, "user_id", None),
        "provider": getattr(req_ctx, "provider", None),
        "notion_api_key": getattr(req_ctx, "notion_api_key", None),
    }
    
    print(f" [extract_context] Fallback - user_id={mcp_context.get('user_id')}, "
          f"has_notion_token={bool(mcp_context.get('notion_api_key'))}")
    
    return mcp_context

def get_notion_connector(context_dict: dict):
    """Crea la instancia del conector usando el diccionario extraído"""
    api_key = context_dict.get("notion_api_key")
    
    if not api_key:
        raise ValueError("Falta notion_api_key en el contexto decodificado")
        
    # Aquí creamos el conector que definimos en NotionConnector
    return NotionConnector(api_key=api_key)


# =================================================================
#                         TOOLS DE NOTION
# =================================================================

@mcp.tool()
async def notion_search(context: Context, query: str):
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_notion_connector(mcp_context)
    return await connector.search(query)

@mcp.tool()
async def notion_get_page(context: Context, page_id: str):
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_notion_connector(mcp_context)
    return await connector.get_page(page_id)

@mcp.tool()
async def notion_get_block_children(context: Context, block_id: str):
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_notion_connector(mcp_context)
    return await connector.get_block_children(block_id)

@mcp.tool()
async def notion_create_page(context: Context, parent_id: str, properties: Dict, is_db_parent: bool = True):
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_notion_connector(mcp_context)
    return await connector.create_page(parent_id, properties, is_db_parent)

@mcp.tool()
async def notion_update_page_properties(context: Context, page_id: str, properties: Dict):
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_notion_connector(mcp_context)
    return await connector.update_page_properties(page_id, properties)

@mcp.tool()
async def notion_append_block_children(context: Context, block_id: str, blocks: List[Dict]):
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_notion_connector(mcp_context)
    return await connector.append_block_children(block_id, blocks)

@mcp.tool()
async def notion_query_database(context: Context, database_id: str, filter_params: Optional[Dict] = None):
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_notion_connector(mcp_context)
    return await connector.query_database(database_id, filter_params)

@mcp.tool()
async def notion_get_database_structure(context: Context,database_id: str):
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_notion_connector(mcp_context)
    return await connector.get_database_structure(database_id)

@mcp.tool()
async def notion_delete_block(context: Context, block_id: str):
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_notion_connector(mcp_context)
    return await connector.delete_block(block_id)


if __name__ == "__main__":
    keep_alive_mcp()
    uvicorn.run(app, host="0.0.0.0", port=8002)