import os
import faulthandler
from pickle import FALSE
from flask import Flask
from flask_cors import CORS
# Rutas v1
from src.api.v1.chat.routes import search_bp, chat_bp
from src.api.v1.auth.github_routes import github_auth_bp
from src.api.v1.auth.google_routes import google_auth_bp
from src.api.v1.auth.onedrive_routes import onedrive_bp
from src.api.v1.auth.user_routes import user_bp, integrations_bp
# Rutas v2
from src.api.v2.chat.routes import chat_bp as chat_v2_bp
from src.api.v2.security.routes import ping_bp, health_bp, ping_logs_bp
# Settings
from extensions import db
from src.core.logging import get_logger
from src.database.settings.connection import DATABASE_URL
from src.services.auth.utils.keep_alive_jarvis import keep_alive
from werkzeug.middleware.proxy_fix import ProxyFix
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

# Inicializamos la aplicación Flask
app = Flask(__name__)
app.secret_key = SECRET_KEY

# Configurar ProxyFix para manejar proxies inversos
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)
CORS(app, supports_credentials=True, origins=[
    "https://gustavocoello.space","https://www.gustavocoello.space",
    "https://mcp-nexus.vercel.app",
    "https://mcp-nexus.onrender.com",
    "https://localhost:8000",
    "https://localhost:8001",
    "https://localhost:8002",
    "http://localhost:5173",
    "https://coello-system-1.onrender.com"
])


# Configuración de la aplicación Flask
uri = DATABASE_URL

app.config["SQLALCHEMY_DATABASE_URI"] = uri

logger.info(f"URI Final aplicada: {uri}")

db.init_app(app)

# Registrar los blueprints de las rutas
"""Mensajes de la IA sin memoria"""
app.register_blueprint(search_bp, url_prefix='/api/search')

"""Mensajes de la IA con memoria"""
app.register_blueprint(chat_bp, url_prefix='/api/chat')

"""Rutas para login con google"""
app.register_blueprint(google_auth_bp)

"""Autenticación de usuario con github"""
app.register_blueprint(github_auth_bp)

"""Rutas de OneDrive"""
app.register_blueprint(onedrive_bp, url_prefix='/api/onedrive')

"""Rutas de usuario"""
app.register_blueprint(user_bp, url_prefix="/api/v1/user")

"""Rutas de integraciones"""
app.register_blueprint(integrations_bp, url_prefix="/api/v1/integrations")

# ----------- V2 ---------------
"""Rutas de seguridad v2"""
app.register_blueprint(ping_bp, url_prefix="/v2")

app.register_blueprint(health_bp, url_prefix="/v2")

app.register_blueprint(ping_logs_bp, url_prefix="/v2")

app.register_blueprint(chat_v2_bp, url_prefix="/api/v2/chat")


# --- MODO PRODUCCION (Linux/Render) ---
if ENV == "prod":
    if not getattr(app, "keep_alive_started", False):
        keep_alive()
        app.keep_alive_started = True
        print("Keep-alive Jarvis iniciado para Produccion")

if __name__ == "__main__":
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
    app.run(debug=True, host=HOST, port=PORT, use_reloader=False)
