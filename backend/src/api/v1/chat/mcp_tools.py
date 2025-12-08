# src/routes/mcp_tools.py
from flask import Blueprint, jsonify
from src.services.auth.clerk.clerk_middleware import clerk_required

mcp_tools_bp = Blueprint('mcp_tools', __name__)

@mcp_tools_bp.route('/tools', methods=['GET'], strict_slashes=False)
def list_available_tools():
    """
    Lista todas las herramientas MCP disponibles.
    No requiere autenticación ya que solo expone metadata pública.
    """
    tools = [
        {
            "name": "google_resumen_diario",
            "description": "Resumen diario de todos los calendarios o calendario seleccionado",
            "category": "calendar"
        },
        {
            "name": "google_resumen_semanal",
            "description": "Resumen semanal de todos los calendarios o calendario seleccionado",
            "category": "calendar"
        },
        {
            "name": "google_disponibilidad_diaria",
            "description": "Espacios libres entre eventos para una fecha dada",
            "category": "calendar"
        },
        {
            "name": "google_disponibilidad_semanal",
            "description": "Espacios libres para los próximos 7 días",
            "category": "calendar"
        },
        {
            "name": "google_listar_calendarios",
            "description": "Lista todos los calendarios disponibles del usuario",
            "category": "calendar"
        }
    ]
    
    return jsonify({
        "tools": tools,
        "total": len(tools)
    }), 200