import faulthandler

from sqlalchemy import false
faulthandler.enable()
import os
from pickle import FALSE
from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_session import Session

from redis import Redis

from src.services.auth.user_loader import load_user
from src.config.config import Config
from src.services.extensions.limiter import limiter

from extensions import db
from src.config.logging_config import get_logger
from src.api.v1.chat.routes import search_bp, chat_bp
from src.api.v1.auth.github_routes import github_auth_bp
from src.api.v1.auth.google_routes import google_auth_bp
from src.api.v1.auth.routes import auth_bp
from src.services.extensions.onedrive import onedrive_bp
from src.database.config.connection import get_database_url
from dotenv import load_dotenv


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

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.user_loader(load_user)
CORS(app, supports_credentials=True, origins=[
    "https://mcp-nexus-h6y32pgox-gustavo-coellos-projects.vercel.app",
    "https://mcp-nexus.vercel.app",
    "https://mcp-nexus.onrender.com",
    "http://localhost:3000/",
    "http://localhost:3000",
    "http://localhost:8000/mcp/",
    "https://inspector.use-mcp.dev",
    "https://inspector.use-mcp.dev/"
])


# Configuración de la aplicación Flask
app.config.from_object(Config)

# Configuración de la base de datos MYSQL o AZURE SQL
app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
# Configuración Redis para sesiones
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


# Limitar - login -
limiter.init_app(app)


# Inicia el servidor Flask
if __name__ == "__main__":
    is_prod = os.getenv("RENDER", False)
    
    if not is_prod:
        app.run(debug=True, host=HOST, port=PORT) # Poner debug=False en producción

