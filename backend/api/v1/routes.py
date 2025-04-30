from src.services.ai_providers.utils import generate_prompt
from flask import Blueprint, jsonify, request
from config.logging_config import get_logger
import requests


logger = get_logger('routes')

# Create a blueprint for search API
search_bp = Blueprint('search', __name__, url_prefix='/api/search')

@search_bp.route("/prompt", methods=["POST"])
def handle_search_prompt():
    try:
        data = request.json
        if not data or 'prompt' not in data:
            logger.error("No prompt received in request")
            return jsonify({"error": "Prompt is required"}), 400

        logger.debug(f"Search prompt received: {data['prompt']}")
        
        # Process prompt using utils functions
        result = generate_prompt({"description": data['prompt']})
        
        if result == "Todos los servicios de IA no estan disponibles actualmente.":
            return jsonify({"error": result}), 500
            
        return jsonify({"result": result})
    
    except Exception as e:
        error_msg = f"Error processing search prompt: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500


