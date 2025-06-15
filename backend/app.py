from flask import Config, Flask, request, jsonify, Request
from flask_cors import CORS
from src.config.logging_config import get_logger
from src.api.v1.routes import search_bp, chat_bp
from src.config.config import Config
from extensions import db
from dotenv import load_dotenv
import os 

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

app.config.from_object(Config)

db.init_app(app)
# Registrar los blueprints de las rutas
"""Mensajes de la IA sin memoria"""
app.register_blueprint(search_bp, url_prefix='/api/search')
"""Mensajes de la IA con memoria"""
app.register_blueprint(chat_bp, url_prefix='/api/chat')


with app.app_context():
    from src.database.models.models import Chat, Message
    db.create_all()

# Inicia el servidor Flask
if __name__ == "__main__":
    app.run(debug=True, host=HOST, port=PORT)
