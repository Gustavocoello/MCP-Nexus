import uuid
import json 
import asyncio
from typing import List, Optional
from langchain_core.tools import tool, Tool 

from .helpers import _run, _parse_mcp_result

from src.database.models.models import Message
from src.services.mcps.client.client_manager import MCPClientManager

# ----- MCP CONTEXT7 TOOLS (EN client_context7.py) -----
    
def build_koda_context7_tools(user_id: str, chat_id: Optional[str] = None, db_session=None) -> List[Tool]:
    """
    Factory: Obtiene dinámicamente las herramientas de documentación de Context7.
    Nota: Requiere ser ejecutado dentro de un contexto asíncrono para extraerlas,
    por lo que usamos el _run() síncrono para la fase de construcción.
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "koda_context7"
    
    def _record_tool_usage(tool_name: str):
        """Guarda un registro en BD de la herramienta utilizada."""
        if not db_session or not chat_id:
            return
        
        mcp_context_str = json.dumps({
            "tool_used": tool_name,
            "provider": provider_name
        })
        
        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context_str)
        db_session.add(mcp_msg)
        db_session.commit()
    
    async def _fetch_tools():
        client = manager.get_client("context7")
        
        async with client as ctx7:
            return await ctx7.get_langchain_tools()   
    try:
        # Extraemos las tools sincrónicamente al iniciar el Agente
        tools = _run(_fetch_tools())
        return tools
    except Exception as e:
        print(f"Error building Context7 tools: {e}")
        return []