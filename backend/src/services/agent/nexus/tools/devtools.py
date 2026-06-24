import json
from typing import Optional, Dict, List
from langchain_core.tools import tool, Tool
from langchain_core.tools import StructuredTool
from .helpers import _clean_id, _parse_args, _parse_mcp_result, _run
from src.services.mcps.client.client_manager import MCPClientManager
from src.services.agent.common.helpers import mcp_offline_error, mcp_no_client


# Base de datos y Chat 
from src.database.models.models import Message


# --- DEVTOOLS TOOLS ---
def build_devtools_tools(user_id: str, chat_id: Optional[str] = None, db_session=None, client_type: str = "web") -> List[Tool]:
    """
    Factory: genera las tools de Chrome DevTools vinculadas a un user_id.
    Se conecta dinámicamente al servidor MCP para extraer las tools y envuelve
    sus ejecuciones para guardar un historial en la BD.
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "devtools"

    def get_devtools_client():
        return manager.get_client(provider_name)
    
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

    async def fetch_tools():
        client = get_devtools_client()
        
        # Entramos en el contexto para inicializar la sesión MCP.
        # Esto permite que client.get_langchain_tools() lea el esquema exitosamente.
        async with client:
            tools = await client.get_langchain_tools()
            
            wrapped_tools = []
            for t in tools:
                original_sync = t.func
                original_async = t.coroutine
                
                # Creamos closures para atrapar el nombre e inyectar el logging a la base de datos
                def make_sync_wrapper(name, orig_func):
                    def sync_wrapper(*args, **kwargs):
                        _record_tool_usage(name)
                        return orig_func(*args, **kwargs)
                    return sync_wrapper

                def make_async_wrapper(name, orig_coro):
                    async def async_wrapper(*args, **kwargs):
                        _record_tool_usage(name)
                        return await orig_coro(*args, **kwargs)
                    return async_wrapper

                # Recreamos el StructuredTool para no mutar el objeto original 
                # y mantener la compatibilidad con los validadores de Pydantic
                wrapped_tool = StructuredTool.from_function(
                    func=make_sync_wrapper(t.name, original_sync),
                    coroutine=make_async_wrapper(t.name, original_async) if original_async else None,
                    name=t.name,
                    description=t.description,
                    args_schema=t.args_schema
                )
                wrapped_tools.append(wrapped_tool)
                
            return wrapped_tools

    try:
        # Extraemos todo sincronamente antes de pasárselo al LLM
        return _run(fetch_tools())
    except Exception as e:
        print(f"Error cargando tools de DevTools: {str(e)}")
        return []