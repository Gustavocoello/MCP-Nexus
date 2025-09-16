from flask import Blueprint, jsonify
import datetime

ping_bp = Blueprint("ping_bp", __name__)

@ping_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "ok",
        "message": "pong",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    })
