# api/mcp/routes.py
from dataclasses import asdict
from src.mcps.core.models import Event
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from src.config.logging_config import get_logger
from src.mcps.core.context_manager import ContextManager

logger = get_logger("mcp.routes")

3 # --------------------- GOOGLE CALENDAR MCP ---------------------
mcp_bp = Blueprint('mcp', __name__, url_prefix='/api/mcp/calendar')
manager = ContextManager()

def parse_event(data):
    """Convierte un dict en un objeto Event."""
    return Event(
        title=data["title"],
        description=data.get("description"),
        start_time=datetime.fromisoformat(data["start_time"]),
        end_time=datetime.fromisoformat(data["end_time"]),
        location=data.get("location"),
        attendees=data.get("attendees"),
        source=data.get("source", "google_calendar"),
        id=data.get("id")
    )

# --------------------- RUTAS BÁSICAS ---------------------

# ----------------- GET ---------------------
@mcp_bp.route('/conflicts', methods=['GET'])
def get_conflicts():
    try:
        start = datetime.fromisoformat(request.args.get("start"))
        end = datetime.fromisoformat(request.args.get("end"))
        events = manager.get_conflicts(start, end)
        return jsonify([e.__dict__ for e in events]), 200
    except Exception as e:
        logger.exception("Error detectando conflictos")
        return jsonify({"error": str(e)}), 500


@mcp_bp.route('/free-slots', methods=['GET'])
def get_free_slots():
    try:
        start = datetime.fromisoformat(request.args.get("start"))
        end = datetime.fromisoformat(request.args.get("end"))
        duration = int(request.args.get("duration", 30))
        slots = manager.get_free_slots(start, end, duration)
        return jsonify(slots), 200
    except Exception as e:
        logger.exception("Error buscando espacios libres")
        return jsonify({"error": str(e)}), 500


@mcp_bp.route('/summary/daily', methods=['GET'])
def get_daily_summary():
    try:
        calendar_id = request.args.get("calendar_id")
        timezone = request.args.get("timezone", "UTC")
        summary = manager.get_daily_summary(calendar_id=calendar_id, timezone=timezone)
        return jsonify({"summary": summary}), 200
    except Exception as e:
        logger.exception("Error en resumen diario")
        return jsonify({"error": str(e)}), 500


@mcp_bp.route('/summary/weekly', methods=['GET'])
def get_weekly_summary():
    try:
        calendar_id = request.args.get("calendar_id")
        timezone = request.args.get("timezone", "UTC")
        summary = manager.get_weekly_summary(calendar_id=calendar_id, timezone=timezone)
        return jsonify({"summary": summary}), 200
    except Exception as e:
        logger.exception("Error en resumen semanal")
        return jsonify({"error": str(e)}), 500


@mcp_bp.route('/calendars', methods=['GET'])
def list_calendars():
    try:
        calendars = manager.list_calendars()
        return jsonify({"calendars": calendars}), 200
    except Exception as e:
        logger.exception("Error al listar calendarios")
        return jsonify({"error": str(e)}), 500


# ----------------- POST ---------------------

@mcp_bp.route('/create', methods=['POST'])
def create_event():
    try:
        data = request.json
        event = parse_event(data)
        result = manager.create_event(event)
        return jsonify(result), 201
    except Exception as e:
        logger.exception("Error creando evento")
        return jsonify({"error": str(e)}), 500

@mcp_bp.route('/nlp', methods=['POST'])
def parse_nlp_event():
    try:
        text = request.json["text"]
        event = manager.parse_natural_input(text)
        return jsonify(event.__dict__), 200
    except Exception as e:
        logger.exception("Error procesando input natural")
        return jsonify({"error": str(e)}), 500


# ----------------- PUT ---------------------

@mcp_bp.route('/update/<event_id>', methods=['PUT'])
def update_event(event_id):
    try:
        updates = request.json
        result = manager.update_event(event_id, updates)
        return jsonify(result), 200
    except Exception as e:
        logger.exception("Error actualizando evento")
        return jsonify({"error": str(e)}), 500


# ----------------- DELETE ---------------------

@mcp_bp.route('/delete/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    try:
        success = manager.delete_event(event_id)
        return jsonify({"deleted": success}), 200
    except Exception as e:
        logger.exception("Error eliminando evento")
        return jsonify({"error": str(e)}), 500

