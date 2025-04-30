from re import search
from flask import Flask, request, jsonify, Request
from flask_cors import CORS
from config.logging_config import get_logger
from api.v1.routes import search_bp
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
CORS(app)

app.register_blueprint(search_bp, url_prefix='/api/search')

# Inicia el servidor Flask
if __name__ == "__main__":
    app.run(debug=True, host=HOST, port=PORT)