import os
import faulthandler
from pickle import FALSE
from flask import Flask
from flask_cors import CORS

from redis import Redis
from src.config.config import Config
from werkzeug.middleware.proxy_fix import ProxyFix
from src.services.integrations.extensions.limiter import limiter

from extensions import db
from src.config.logging_config import get_logger
from src.api.v1.chat.routes import search_bp, chat_bp
from src.api.v1.chat.mcp_tools import mcp_tools_bp
from src.api.v1.auth.github_routes import github_auth_bp
from src.api.v1.auth.google_routes import google_auth_bp
from src.api.v1.auth.user_routes import user_bp, integrations_bp
from src.api.v2.security.routes import ping_bp, health_bp
from src.services.integrations.extensions.onedrive import onedrive_bp
from src.database.config.connection import get_database_url
from src.services.auth.utils.keep_alive_jarvis import keep_alive
from dotenv import load_dotenv

faulthandler.enable()

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configuración de las variables
PORT = os.getenv("PORT", 5000)
HOST = os.getenv("HOST", "0.0.0.0")
SECRET_KEY = os.getenv("SECRET_KEY")

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
    "http://localhost:8000/mcp",
    "https://localhost:8001",
    "http://localhost:5173",
    "https://coello-system-1.onrender.com"
])


# Configuración de la aplicación Flask
app.config.from_object(Config)
uri = get_database_url()
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

"""Rutas de seguridad v2"""
app.register_blueprint(ping_bp, url_prefix="/v2")

app.register_blueprint(health_bp, url_prefix="/v2")

"""Rutas de usuario"""
app.register_blueprint(user_bp, url_prefix="/api/v1/user")

"""Rutas de integraciones"""
app.register_blueprint(integrations_bp, url_prefix="/api/v1/integrations")

"""Rutas de herramientas MCP"""
app.register_blueprint(mcp_tools_bp, url_prefix='/api/v1/mcp')

# Limitar - login -
limiter.init_app(app)

# Iniciar keep-alive SOLO si se especifica la variable de entorno
# (necesario para Render donde gunicorn no ejecuta if __name__)
INIT_KEEP_ALIVE = os.getenv("INIT_KEEP_ALIVE").lower() == "true"

if INIT_KEEP_ALIVE and not getattr(app, "keep_alive_started", False):
    keep_alive()
    app.keep_alive_started = True
    print("🚀 Keep-alive Jarvis iniciado (vía INIT_KEEP_ALIVE)")

# Inicia el servidor Flask (solo desarrollo local)
if __name__ == "__main__":
    is_prod = os.getenv("RENDER", False)
    
    # Iniciar keep-alive si NO se inició arriba
    if not getattr(app, "keep_alive_started", False):
        keep_alive()
        app.keep_alive_started = True
        print("🚀 Keep-alive Jarvis iniciado (vía if __name__)")
    
    if not is_prod:
        app.run(debug=True, host=HOST, port=PORT, use_reloader=False)
