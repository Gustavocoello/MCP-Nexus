import os
import faulthandler
from pickle import FALSE
from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_session import Session

from redis import Redis

from src.services.auth.user_loader import load_user
from src.config.config import Config
from src.services.integrations.extensions.limiter import limiter

from extensions import db
from src.config.logging_config import get_logger
from src.api.v1.chat.routes import search_bp, chat_bp
from src.api.v1.auth.github_routes import github_auth_bp
from src.api.v1.auth.google_routes import google_auth_bp
from src.api.v1.auth.routes import auth_bp
from src.api.v2.security.routes import ping_bp
from src.services.integrations.extensions.onedrive import onedrive_bp
from src.database.config.connection import get_database_url
from src.services.auth.keep_alive_jarvis import keep_alive
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

app.config.update(
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=True,
    REMEMBER_COOKIE_SAMESITE='None',
    REMEMBER_COOKIE_SECURE=True
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.user_loader(load_user)
CORS(app, supports_credentials=True, origins=[
    "https://mcp-nexus-h6y32pgox-gustavo-coellos-projects.vercel.app",
    "https://mcp-nexus.vercel.app",
    "https://mcp-nexus.onrender.com",
    "http://localhost:8000/mcp/",
    "https://localhost:8001",
    "http://localhost:5173",
    "https://gustavocoello.space",
    "https://coello-system-1.onrender.com"
])


# Configuración de la aplicación Flask
app.config.from_object(Config)

# Configuración de la base de datos MYSQL o AZURE SQL
app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
app.config['SESSION_TYPE'] = 'redis' # redis para prod y filesystem para local
app.config['SESSION_REDIS'] = Redis.from_url(app.config["REDIS_URL"])
Session(app)

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

"""Autenticación de usuario"""
app.register_blueprint(auth_bp)

"""Rutas de OneDrive"""
app.register_blueprint(onedrive_bp, url_prefix='/api/onedrive')

"""Rutas de seguridad v2"""
app.register_blueprint(ping_bp, url_prefix="/v2")

# Limitar - login -
limiter.init_app(app)

# Inicia el servidor Flask
if __name__ == "__main__":
    
    is_prod = os.getenv("RENDER", False)
    # Iniciamos la función keep_alive para mantener el servidor activo
    # Solo inicia keep_alive en el proceso principal (no en el reloader)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not os.getenv("FLASK_DEBUG"):
        keep_alive()
    
    if not is_prod:
        app.run(debug=True, host=HOST, port=PORT) # Poner debug=False en producción

