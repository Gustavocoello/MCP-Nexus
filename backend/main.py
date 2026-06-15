import os
import uvicorn
import faulthandler
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
# Rutas v1
from src.api.v1.chat.routes import search_router, chat_router
from src.api.v1.auth.google_routes import google_auth_router
from src.api.v1.auth.github_routes import github_auth_router
from src.api.v1.auth.onedrive_routes import onedrive_router
from src.api.v1.auth.user_routes import user_router, integrations_router

# Los routers v2 y de telemetría
from src.api.v2.chat.routes import chat_v2_router
from src.api.v2.admin.routes import hitl_router
from src.api.v2.security.routes import ping_router, ping_logs_router, health_router
# Settings
from src.core.logging import get_logger
from src.database.settings.connection import DATABASE_URL
from src.services.auth.utils.keep_alive_jarvis import keep_alive
from dotenv import load_dotenv

faulthandler.enable()

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configuración de las variables
PORT = os.getenv("PORT", 5000)
HOST = os.getenv("HOST", "0.0.0.0")
SECRET_KEY = os.getenv("SECRET_KEY")
ENV = os.getenv("ENV").lower()
SYNC_ON_START = os.getenv("SYNC_ON_START").lower() == "true"

# Configurar logging
logger = get_logger('app')

# --- EVENTOS DE INICIO Y APAGADO (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lógica de inicio (Startup)
    logger.info(f"URI Final aplicada: {DATABASE_URL}")
    
    # MODO PRODUCCION (Linux/Render)
    if ENV == "prod":
        keep_alive()
        logger.info("Keep-alive Jarvis iniciado para Produccion")
        
    # Hidratacion de Datos (Linux -> Windows)
    if ENV == "dev" and SYNC_ON_START:
        print("\n" + "="*50)
        print("HIDRATANDO ENTORNO DEV: Sincronizando Linux -> Windows...")
        print("="*50)
        try:
            from src.database.tools.auto_sync import AutoSync
            auto_sync = AutoSync()
            if auto_sync.run_sync(source='linux', targets=['windows']):
                print("Datos sincronizados con exito. Listo para programar.")
            else:
                print("Advertencia: Hubo un problema sincronizando algunos datos.")
        except Exception as e:
            print(f"Error al iniciar Auto-Sync: {e}")
        print("="*50 + "\n")
    
    yield # La aplicación se ejecuta aquí
    
    # Lógica de apagado (Shutdown) opcional
    logger.info("Apagando la aplicación...")

app = FastAPI(lifespan=lifespan, title="Agentes API")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gustavocoello.space",
        "https://www.gustavocoello.space",
        "https://mcp-nexus.vercel.app",
        "https://mcp-nexus.onrender.com",
        "https://localhost:8000",
        "https://localhost:8001",
        "https://localhost:8002",
        "http://localhost:5173",
        "https://coello-system-1.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Permite todos los headers
)

# --- REGISTRO DE RUTAS ---
# Rutas v1
app.include_router(search_router, prefix='/api/v1/search')
app.include_router(chat_router, prefix='/api/v1/chat')
app.include_router(google_auth_router)
app.include_router(github_auth_router)
app.include_router(user_router)
app.include_router(onedrive_router, prefix='/api/v1/onedrive')
app.include_router(integrations_router, prefix="/api/v1/integrations")

# Rutas v2
app.include_router(ping_router, prefix="/v2")
app.include_router(health_router, prefix="/v2")
app.include_router(ping_logs_router, prefix="/v2")
app.include_router(chat_v2_router, prefix="/api/v2/chat")

# --- Monitoring ---
app.include_router(ping_router)
app.include_router(ping_logs_router)
app.include_router(health_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=HOST, 
        port=PORT, 
        reload=(ENV == "dev"), 
        proxy_headers=True, 
        forwarded_allow_ips="*"
    )

# uvicorn main:app --reload --port 5000