# src/services/agent/lamar/tool.py
from src.core.logging import get_logger

from .tools.token_monitor import build_token_monitor_tools
from .tools.service_pinger import build_service_pinger_tools
from .tools.llm_monitor import build_llm_monitor_tools

logger = get_logger("lamar_tools")

def build_lamar_tools() -> list:
    """
    Agrupa y retorna todas las herramientas de infraestructura para Lamar.
    """
    tools = [
        *build_token_monitor_tools(),
        *build_service_pinger_tools(),
        *build_llm_monitor_tools(),
    ]
    
    logger.info(f"Loaded {len(tools)} tools for Lamar DevOps Agent")
    return tools