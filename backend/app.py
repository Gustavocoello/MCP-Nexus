from pickle import FALSE
from flask import Flask
from flask_cors import CORS
import os

from httpx import get
from sqlalchemy import true 
from src.config.config import Config

from extensions import db
from src.config.logging_config import get_logger
from src.api.v1.routes import search_bp, chat_bp
from src.database.config.connection import get_database_url
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configuración de las variables
PORT = os.getenv("PORT", 5000)
HOST = os.getenv("HOST", "0.0.0.0")

# Configurar logging
logger = get_logger('app')

# Inicializamos la aplicación Flask
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Configuración de la aplicación Flask
app.config.from_object(Config)

# Configuración de la base de datos MYSQL o AZURE SQL
app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()  # Usar la función para obtener la URL de conexión

db.init_app(app)

# Registrar los blueprints de las rutas
"""Mensajes de la IA sin memoria"""
app.register_blueprint(search_bp, url_prefix='/api/search')
"""Mensajes de la IA con memoria"""
app.register_blueprint(chat_bp, url_prefix='/api/chat')

pass

# Inicia el servidor Flask
if __name__ == "__main__":
    app.run(debug=True, host=HOST, port=PORT) # Poner debug=False en producción
