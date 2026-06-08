# src/mcps/server/github_server.py
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

# --- Importamos el Conector de GitHub que creamos ---
from source.github_connection import GithubConnector

# --- Tu Helper de Tiempo ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))

from utils.time_helper import get_now
from utils.keep_alive_mcp import keep_alive_mcp

load_dotenv()

# Añadir la clave secreta de autenticación (Jarvis y MCP deben compartirla)
MCP_SECRET_KEY = os.getenv("MCP_SECRET_KEY")
# Asegúrate de que la clave secreta se cargó
if not MCP_SECRET_KEY:
    print("ADVERTENCIA: La clave secreta MCP_SECRET_KEY no está configurada.")

# Contexto para JWT
_current_request_context: ContextVar[dict] = ContextVar('github_mcp_context', default={})

# Middleware modificado para almacenar el contexto globalmente
class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware para validar JWT en requests al MCP Server de GitHub"""
    
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
                "user_id": payload.get("sub"),
                "provider": payload.get("provider"),
                "github_token": payload.get("github_token"), # Extraído del JWT del backend
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
mcp = FastMCP(name="Github MCP Server")

# Configuración de la App Starlette
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
        Route("/ping", lambda r: JSONResponse({"status": "ok", "service": "github-mcp"}))
    ], 
    lifespan=mcp_app.lifespan
)

#==================== HELPERS =====================
def extract_context_from_fastmcp(context: Context) -> dict:
    """Extrae el contexto MCP desde la variable global o el fallback de FastMCP"""
    mcp_context = _current_request_context.get()
    
    print(f" [extract_context] Contexto Global: user_id={mcp_context.get('user_id')}, "
          f"has_github_token={bool(mcp_context.get('github_token'))}")
    
    if mcp_context and mcp_context.get('github_token'):
        return mcp_context.copy()
    
    # Fallback: intentar desde request_context
    req_ctx = context.request_context
    mcp_context = {
        "user_id": getattr(req_ctx, "user_id", None),
        "provider": getattr(req_ctx, "provider", None),
        "github_token": getattr(req_ctx, "github_token", None),
    }
    
    print(f" [extract_context] Fallback - user_id={mcp_context.get('user_id')}, "
          f"has_github_token={bool(mcp_context.get('github_token'))}")
    
    return mcp_context

def get_github_connector(context_dict: dict):
    """Crea la instancia del conector usando el diccionario extraído"""
    api_key = context_dict.get("github_token")
    
    if not api_key:
        raise ValueError("Falta github_token en el contexto decodificado")
        
    return GithubConnector(api_key=api_key)

def _extract_id(value: str) -> str:
    """Sanitiza el string recibido (evita fallos si el LLM manda JSON anidado)"""
    if not value or not isinstance(value, str):
        return value
    value = value.strip()
    if value.startswith("{"):
        try:
            parsed = _json.loads(value)
            return str(next(iter(parsed.values())))
        except Exception:
            pass
    return value

# =================================================================
#                        TOOLS DE GITHUB
# =================================================================

@mcp.tool()
async def github_search_repositories(context: Context, query: str):
    query = _extract_id(query)
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_github_connector(mcp_context)
    return await connector.search_repositories(query)

@mcp.tool()
async def github_search_code(context: Context, query: str):
    query = _extract_id(query)
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_github_connector(mcp_context)
    return await connector.search_code(query)

@mcp.tool()
async def github_get_file_contents(context: Context, owner: str, repo: str, path: str, branch: Optional[str] = None):
    owner = _extract_id(owner)
    repo = _extract_id(repo)
    path = _extract_id(path)
    if branch: branch = _extract_id(branch)
    
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_github_connector(mcp_context)
    return await connector.get_file_contents(owner, repo, path, branch)

@mcp.tool()
async def github_create_or_update_file(context: Context, owner: str, repo: str, path: str, content: str, message: str, branch: str, sha: Optional[str] = None):
    owner = _extract_id(owner)
    repo = _extract_id(repo)
    path = _extract_id(path)
    branch = _extract_id(branch)
    if sha: sha = _extract_id(sha)
    
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_github_connector(mcp_context)
    return await connector.create_or_update_file(owner, repo, path, content, message, branch, sha)

@mcp.tool()
async def github_create_branch(context: Context, owner: str, repo: str, ref: str, sha: str):
    owner = _extract_id(owner)
    repo = _extract_id(repo)
    ref = _extract_id(ref)
    sha = _extract_id(sha)
    
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_github_connector(mcp_context)
    return await connector.create_branch(owner, repo, ref, sha)

@mcp.tool()
async def github_create_pull_request(context: Context, owner: str, repo: str, title: str, head: str, base: str, body: Optional[str] = None):
    owner = _extract_id(owner)
    repo = _extract_id(repo)
    head = _extract_id(head)
    base = _extract_id(base)
    
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_github_connector(mcp_context)
    return await connector.create_pull_request(owner, repo, title, head, base, body)

@mcp.tool()
async def github_get_issue(context: Context, owner: str, repo: str, issue_number: int):
    owner = _extract_id(owner)
    repo = _extract_id(repo)
    
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_github_connector(mcp_context)
    return await connector.get_issue(owner, repo, issue_number)

@mcp.tool()
async def github_get_branch_sha(context: Context, owner: str, repo: str, branch: str = "main"):
    owner = _extract_id(owner)
    repo = _extract_id(repo)
    branch = _extract_id(branch)
    
    mcp_context = extract_context_from_fastmcp(context)
    connector = get_github_connector(mcp_context)
    return await connector.get_branch_sha(owner, repo, branch)


if __name__ == "__main__":
    keep_alive_mcp()
    uvicorn.run(app, host="0.0.0.0", port=8004) # Puerto 8004 para GitHub