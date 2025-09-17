from flask import Blueprint, jsonify, request
from src.config.logging_config import get_logger
from datetime import datetime

logging = get_logger(__name__)

ping_bp = Blueprint("ping_bp", __name__)

@ping_bp.route("/ping", methods=["GET"])
def ping():
    client_ip = request.remote_addr  # la IP de quien hizo el ping
    user_agent = request.headers.get("User-Agent", "unknown")
    now = datetime.utcnow().isoformat() + "Z"
    logging.info(f"[PONG] Backend recibió solicitud /v2/ping a las {now}")
    return jsonify({
        "status": "pong",
        "message": "Render server is alive! - Backend odoo",
        "client_ip": client_ip,
        "user_agent": user_agent,
        "timestamp": now
    })
