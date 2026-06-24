# src/services/agent/lamar/tool.py
from src.core.logging import get_logger

from .tools.token_monitor import build_token_monitor_tools
from .tools.service_pinger import build_service_pinger_tools
from .tools.llm_monitor import build_llm_monitor_tools

logger = get_logger("lamar_tools")

def build_lamar_tools(user_id: str, client_type: str = "web") -> list:
    """
    Agrupa y retorna todas las herramientas de infraestructura para Lamar.
    """
    tools = [
        *build_token_monitor_tools(user_id, client_type=client_type),
        *build_service_pinger_tools(user_id, client_type=client_type),
        *build_llm_monitor_tools(user_id, client_type=client_type),
    ]
    
    logger.info(f"Loaded {len(tools)} tools for Lamar DevOps Agent")
    return tools