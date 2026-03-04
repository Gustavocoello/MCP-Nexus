from flask import Blueprint, jsonify, request
from extensions import db
from http import HTTPStatus
from datetime import datetime, timezone # Cambiado de utcnow (deprecated)
from src.config.time_helper import get_now
from src.config.logging_config import get_logger
from src.database.config.azure.azure_config import test_connection_health, get_pool_stats 
  
logging = get_logger(__name__)

ping_bp = Blueprint("ping_bp", __name__)
health_bp = Blueprint('health', __name__)

@ping_bp.route("/ping", methods=["GET"])
def ping():
    client_ip = request.remote_addr
    user_agent = request.headers.get("User-Agent", "unknown")
    # Usar timezone-aware datetime para evitar problemas de servidor
    now = get_now().isoformat()
    logging.info(f"[PONG] Backend recibió solicitud /v2/ping a las {now}")
    return jsonify({
        "status": "pong",
        "message": "Render server is alive! - Backend ",
        "client_ip": client_ip,
        "user_agent": user_agent,
        "timestamp": now
    })

@health_bp.route("/db-health", methods=["GET"])
def db_health_check_route():
    """
    Función de Health Check que utiliza la función auxiliar para despertar Azure.
    """
    try:
        # IMPORTANTE: Usamos db.engine (sin paréntesis)
        engine = db.engine
        health_data = test_connection_health(engine)
        
        if health_data.get('status') == 'unhealthy':
            logging.error(f"DB Health Check Falló: {health_data.get('error')}")
            return jsonify(health_data), HTTPStatus.SERVICE_UNAVAILABLE
        
        logging.info("DB Health Check Exitoso (Azure está despierto)")
        return jsonify(health_data), HTTPStatus.OK
    except Exception as e:
        logging.error(f"Error crítico en health check: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@health_bp.route('/pool-stats', methods=['GET'])
def pool_stats_endpoint():
    """
    Endpoint para monitorear el pool de conexiones y evitar fugas de RAM.
    """
    try:
        # Corregido: db.engine es una propiedad
        engine = db.engine 
        stats_data = get_pool_stats(engine) 
        return jsonify(stats_data), HTTPStatus.OK
    except Exception as e:
        return jsonify({"error": str(e)}), 500