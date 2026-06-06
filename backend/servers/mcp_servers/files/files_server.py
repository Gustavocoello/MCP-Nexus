# src/mcps/server/files_server.py
import os
import sys
import jwt
import pytz
import uvicorn
import json as _json
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
from sources.file_manager import list_local_directory, read_local_file, patch_local_file

# --- Tu Helper de Tiempo ---

current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from utils.time_helper import get_now
from utils.Keep_alive_mcp import keep_alive_mcp

load_dotenv()

# Añadir la clave secreta de autenticación (Jarvis y MCP deben compartirla)
MCP_SECRET_KEY = os.getenv("MCP_SECRET_KEY")
# Asegúrate de que la clave secreta se cargó
if not MCP_SECRET_KEY:
    print("ADVERTENCIA: La clave secreta MCP_SECRET_KEY no está configurada.")

# Contexto para JWT
_current_request_context: ContextVar[dict] = ContextVar('file_mcp_context', default={})

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
            print(f" - user_id: {payload.get('sub')}")
            print(f" - provider: {payload.get('provider')}")
            
            # Guardar en variable global
            mcp_context = {
                "user_id": payload.get("sub"), # sub (Subject): Es el identificador único del usuario (el "sujeto" del token). - User_id 
                "provider": payload.get("provider"),
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
mcp = FastMCP(name="Files MCP Server")

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
        Route("/ping", lambda r: JSONResponse({"status": "ok", "service": "files-mcp"}))
    ], 
    lifespan=mcp_app.lifespan
)

#==================== HELPERS =====================
def extract_context_from_fastmcp(context: Context) -> dict:
    """Extrae el contexto MCP desde la variable global o el fallback de FastMCP"""
    mcp_context = _current_request_context.get()
    
    print(f" [extract_context] Contexto Global: user_id={mcp_context.get('user_id')} ")
    
    if mcp_context and mcp_context.get('notion_api_key'):
        return mcp_context.copy()
    
    # Fallback: intentar desde request_context (Igual que en Calendar)
    req_ctx = context.request_context
    mcp_context = {
        "user_id": getattr(req_ctx, "user_id", None),
        "provider": getattr(req_ctx, "provider", None),
    }
    
    print(f" [extract_context] Fallback - user_id={mcp_context.get('user_id')} ")
    
    return mcp_context



# =================================================================
#             FILES TOOLS
# =================================================================

@mcp.tool()
async def mcp_list_directory(context: Context, directory_path: str = "."):
    """Lists files and folders inside a specific directory."""
    user_context = extract_context_from_fastmcp(context)
    print(f"[ACTION] User {user_context.get('user_id')} requested directory list: {directory_path}")
    return list_local_directory(directory_path)

@mcp.tool()
async def mcp_read_file(context: Context, file_path: str):
    """Reads the content of a local file in the workspace."""
    user_context = extract_context_from_fastmcp(context)
    print(f"[ACTION] User {user_context.get('user_id')} requested file read: {file_path}")
    return read_local_file(file_path)

@mcp.tool()
async def mcp_patch_file(context: Context, file_path: str, search_block: str, replace_block: str):
    """Surgically edits an existing file without rewriting the entire document."""
    user_context = extract_context_from_fastmcp(context)
    print(f"[ACTION] User {user_context.get('user_id')} requested file patch: {file_path}")
    return patch_local_file(file_path, search_block, replace_block)

if __name__ == "__main__":
    keep_alive_mcp()
    port = int(os.getenv("PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)