from flask import Blueprint, jsonify, request
from extensions import db
from http import HTTPStatus
from datetime import datetime
from src.config.logging_config import get_logger
from src.database.config.azure_config import  test_connection_health, get_pool_stats 
  
logging = get_logger(__name__)

ping_bp = Blueprint("ping_bp", __name__)

health_bp = Blueprint('health', __name__)

@ping_bp.route("/ping", methods=["GET"])
def ping():
    client_ip = request.remote_addr  # la IP de quien hizo el ping
    user_agent = request.headers.get("User-Agent", "unknown")
    now = datetime.utcnow().isoformat() + "Z"
    logging.info(f"[PONG] Backend recibió solicitud /v2/ping a las {now}")
    return jsonify({
        "status": "pong",
        "message": "Render server is alive! - Backend ",
        "client_ip": client_ip,
        "user_agent": user_agent,
        "timestamp": now
    })

# Solo funciona para la base de datos en produccion
@health_bp.route("/db-health", methods=["GET"])
def db_health_check_route():
    """
    Función de Health Check que utiliza la función auxiliar para despertar Azure.
    """
    engine = db.engine
    
    # Usamos la función robusta definida en el motor (backend.engine)
    health_data = test_connection_health(engine)
    
    # Devuelve 503 si el estado es 'unhealthy' (para que UptimeRobot sepa que falló)
    if health_data.get('status') == 'unhealthy':
        logging.error(f"DB Health Check Falló: {health_data.get('error')}")
        return jsonify(health_data), HTTPStatus.SERVICE_UNAVAILABLE # 503
    
    # Devuelve 200/OK si el estado es 'healthy'
    logging.info("DB Health Check Exitoso (Azure está despierto)")
    return jsonify(health_data), HTTPStatus.OK # 200

@health_bp.route('/pool-stats', methods=['GET'])
def pool_stats_endpoint():
    """
    Endpoint opcional para monitorear el pool de conexiones.
    """
    # Usamos la función importada
    engine = db.engine()
    stats_data = get_pool_stats(engine) 
    return jsonify(stats_data), HTTPStatus.OK