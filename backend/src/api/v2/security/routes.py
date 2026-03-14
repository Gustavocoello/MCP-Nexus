from urllib import response

from flask import Blueprint, jsonify, request
from http import HTTPStatus, client
from src.config.time_helper import get_now
from src.config.logging_config import get_logger
from src.database.models.models import PingLog
from src.database.config.connection import SessionLocal, engine
from src.config.ping.log_parser import parse_ping_log_v1, clean_log_message
from src.database.config.azure.azure_config import test_connection_health, get_pool_stats 
  
logging = get_logger(__name__)

ping_logs_bp = Blueprint('ping_logs', __name__)
ping_bp = Blueprint("ping_bp", __name__)
health_bp = Blueprint('health', __name__)

@ping_logs_bp.route('/ping_log', methods=['POST'])
def receive_ping_log():
    """
    Endpoint centralizado para recibir pings. 
    Usa el mismo patrón de cierre de sesión que los mensajes de chat.
    """
    db_session = SessionLocal() # Instanciamos la sesión localmente
    client_host = request.remote_addr
    
    try:
        # 1. Obtener y validar datos
        try:
            data = request.get_json()
            raw_message = data.get("log", "")
        except Exception:
            return jsonify({"error": "Invalid JSON"}), 400

        if not raw_message:
            return jsonify({"error": "No log provided"}), 400

        # Limpiar caracteres extraños y parsear el mensaje
        cleaned_message = clean_log_message(raw_message)
        # Parsear el log ya limpio
        parsed = parse_ping_log_v1(cleaned_message)
        # Tiempo de respuesta
        response_ms = (get_now() - get_now()).total_seconds() * 1000  
        # Extraer el nombre del servicio 
        service_name = parsed.get("service")
        
        # Si el parser NO lo reconoce, creamos un objeto 'parsed' genérico
        if not parsed:
            parsed = {
                "service": "General-Log",
                "event_type": "info",
                "status_code": 200,
                "message": cleaned_message,
                "next_ping_sc": None
            }
        else:
            service=service_name,
            event_type=parsed.get('event_type'),
            message=parsed.get('message'),
            response_ms=response_ms,
            status_code=parsed.get('status_code'),
            client_ip=client_host,
            next_ping_sc=parsed.get('next_ping_sc'),
            timestamp=get_now()
            
        

        # 3. Crear y guardar el registro
        new_log = PingLog(
            service=service,
            event_type=event_type,
            message=message,
            response_ms=response_ms,
            status_code=status_code,
            client_ip=client_ip,
            next_ping_sc=next_ping_sc,
            timestamp=timestamp
        )
        
        db_session.add(new_log)
        db_session.commit()
        
        return jsonify({
            "status": "ok",
            "service": parsed['service'],
            "timestamp": get_now().isoformat()
        }), 201

    except Exception as e:
        db_session.rollback() # Importante hacer rollback si falla el commit
        logging.exception("Error guardando ping log centralizado")
        return jsonify({"error": str(e)}), 500
        
    finally:
        db_session.close()

@ping_bp.route("/ping", methods=["GET"])
def ping():
    client_ip = request.remote_addr
    user_agent = request.headers.get("User-Agent", "unknown")
    # Usar timezone-aware datetime para evitar problemas de servidor
    now = get_now().isoformat()
    #logging.info(f"[PONG]")
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
    db_session = SessionLocal() # Creamos sesión por si el test la necesita
    try:
        # Usamos el engine directamente para el health check
        health_data = test_connection_health(engine)
        
        if health_data.get('status') == 'unhealthy':
            logging.error(f"DB Health Check Falló: {health_data.get('error')}")
            return jsonify(health_data), HTTPStatus.SERVICE_UNAVAILABLE
        
        # Opcional: Ejecutar una query simple con la sesión para asegurar que el pool sirve
        # db_session.execute(text("SELECT 1")) 

        logging.info("DB Health Check Exitoso (Azure está despierto)")
        return jsonify(health_data), HTTPStatus.OK
        
    except Exception as e:
        logging.error(f"Error crítico en health check: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500
    finally:
        db_session.close() # <--- OBLIGATORIO: Cerramos siempre

@health_bp.route('/pool-stats', methods=['GET'])
def pool_stats_endpoint():
    """
    Endpoint para monitorear el pool de conexiones y evitar fugas de RAM.
    """
    try:
        # get_pool_stats analiza el estado interno del engine (conexiones usadas/libres)
        stats_data = get_pool_stats(engine) 
        return jsonify(stats_data), HTTPStatus.OK
    except Exception as e:
        logging.error(f"Error obteniendo pool stats: {e}")
        return jsonify({"error": str(e)}), 500