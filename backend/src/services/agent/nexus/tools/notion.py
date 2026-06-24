import json
import json as _json
from typing import Optional, Dict, List
from langchain_core.tools import tool, Tool
from .helpers import _clean_id, _parse_args, _parse_mcp_result, _run
from src.services.mcps.client.client_manager import MCPClientManager
from src.services.agent.common.helpers import mcp_offline_error, mcp_no_client


# Base de datos y Chat 
from src.database.models.models import Message

# --- NOTION TOOLS ---

def build_notion_tools(user_id: str, chat_id: Optional[str] = None, db_session=None, client_type: str = "web"):
    """
    Factory: genera las 9 tools de Notion vinculadas a un user_id específico.
    Se llama UNA vez al crear NexusAgent(user_id).
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "notion"

    def get_notion():
        return manager.get_client(provider_name)
    
    def _record_tool_usage(tool_name: str):
        """Guarda un registro ligero en BD de qué herramienta usó el agente."""
        if not db_session or not chat_id:
            return
        
        # 1. Guardar en la Base de Datos (rol: mcp-tool)
        # Solo guardamos el nombre de la herramienta. ¡Nada de JSONs gigantes!
        mcp_context_str = json.dumps({
            "tool_used": tool_name,
            "provider": provider_name
        })
        
        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context_str)
        db_session.add(mcp_msg)
        db_session.commit()

    # ----------------------------------------------------------------

    @tool
    def notion_search(query: str) -> str:
        """
        Busca páginas, bases de datos y bloques en Notion del usuario.
        Usa esto cuando el usuario pregunte por contenido general en su Notion.
        Input: query (str) — término de búsqueda.
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
            
            result = _run(get_notion().notion_search(query=query))
            _record_tool_usage("notion_search")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_search", str(e))
    @tool
    def notion_get_page(page_id: str) -> str:
        """
        Obtiene el contenido completo de una página de Notion por su ID.
        Usa esto cuando ya tienes el page_id y necesitas ver su contenido.
        Input: page_id (str) — ID de la página.
        """
        try:
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")

            result = _run(get_notion().notion_get_page(page_id=page_id))
            _record_tool_usage("notion_get_page")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_get_page", str(e))

    @tool
    def notion_get_block_children(block_id: str) -> str:
        """
        Obtiene los bloques hijos de una página o bloque de Notion.
        Usa esto para leer el contenido interno de una página.
        Input: block_id (str) — ID del bloque o página.
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
            result = _run(get_notion().notion_get_block_children(block_id=block_id))
            _record_tool_usage("notion_get_block_children")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_get_block_children", str(e))

    @tool
    def notion_create_page(parent_id: str, properties: Optional [str] = None, is_db_parent: bool = True) -> str:
        """
        Crea una nueva página en Notion dentro de una base de datos o página padre.
        Usa esto cuando el usuario quiera crear una tarea, nota, o entrada nueva.
        Input: parent_id (str), properties (str JSON), is_db_parent (bool).
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
            args = _parse_args(
                {"parent_id": parent_id, "properties": properties or "", "is_db_parent": is_db_parent},
                ["parent_id", "properties"]
            )
            parent_id = _clean_id(args.get("parent_id", parent_id))
            properties = args.get("properties", properties)
            is_db_parent = args.get("is_db_parent", is_db_parent)
            
            if not properties:
                return "Error: properties es requerido."
            
            props = json.loads(properties) if isinstance(properties, str) else properties
            result = _run(get_notion().notion_create_page(
                parent_id=parent_id, properties=props, is_db_parent=is_db_parent
            ))
            _record_tool_usage("notion_create_page")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_create_page", str(e))

    @tool
    def notion_update_page_properties(page_id: str, properties: Optional [str] = None) -> str:
        """
        Actualiza las propiedades de una página existente en Notion.
        Usa esto para marcar tareas como completadas, cambiar status, fechas, etc.
        Input: page_id (str), properties (str JSON con los campos a actualizar).
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
            args = _parse_args(
                {"page_id": page_id, "properties": properties or ""},
                ["page_id", "properties"]
            )
            page_id = _clean_id(args.get("page_id", page_id))
            properties = args.get("properties", properties)
            
            if not properties:
                return "Error: properties es requerido."

            props = _json.loads(properties) if isinstance(properties, str) else properties
            result = _run(get_notion().notion_update_page_properties(
                page_id=page_id, properties=props
            ))
            _record_tool_usage("notion_update_page_properties")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_update_page_properties", str(e))

    @tool
    def notion_append_block_children(block_id: str, blocks: Optional [str] = None) -> str:
        """
        Añade contenido (bloques) a una página o bloque existente en Notion.
        Usa esto para agregar texto, listas, o notas a una página ya creada.
        Input: block_id (str), blocks (str JSON — lista de bloques Notion).
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
            args = _parse_args(
                {"block_id": block_id, "blocks": blocks or ""},
                ["block_id", "blocks"]
            )
            block_id = _clean_id(args.get("block_id", block_id))
            blocks = args.get("blocks", blocks)
            
            if not blocks:
                return "Error: blocks es requerido."
            
            blocks_list = _json.loads(blocks) if isinstance(blocks, str) else blocks
            result = _run(get_notion().notion_append_block_children(
                block_id=block_id, blocks=blocks_list
            ))
            _record_tool_usage("notion_append_block_children")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_append_block_children", str(e))

    @tool
    def notion_query_database(database_id: str, filter_params: Optional[str] = None) -> str:
        """
        Consulta una base de datos de Notion con filtros opcionales.
        Usa esto para listar tareas, filtrar por status, fecha, prioridad, etc.
        Input: database_id (str), filter_params (str JSON opcional con filtros Notion).
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
            args = _parse_args(
                {"database_id": database_id, "filter_params": filter_params},
                ["database_id"]
            )
            database_id = _clean_id(args.get("database_id", database_id))
            filter_params = args.get("filter_params", filter_params)
        
            params = _json.loads(filter_params) if filter_params else None
            result = _run(get_notion().notion_query_database(
                database_id=database_id, filter_params=params
            ))
            _record_tool_usage("notion_query_database")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_query_database", str(e))

    @tool
    def notion_get_database_structure(database_id: str) -> str:
        """
        Obtiene el esquema (estructura de columnas) de una base de datos Notion.
        Usa esto PRIMERO cuando no conoces las propiedades de una DB antes de crear o filtrar.
        Input: database_id (str).
        """
        try: 
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")
        
            result = _run(get_notion().notion_get_database_structure(database_id=database_id))
            _record_tool_usage("notion_get_database_structure")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_get_database_structure", str(e))

    @tool
    def notion_delete_block(block_id: str) -> str:
        """
        Elimina (archiva) un bloque o página de Notion por su ID.
        Usa esto solo cuando el usuario explícitamente pida eliminar algo.
        Input: block_id (str).
        """
        try:
            client = get_notion()
            if not client:
                return mcp_no_client("Notion")

            result = _run(get_notion().notion_delete_block(block_id=block_id))
            _record_tool_usage("notion_delete_block")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Notion", "notion_delete_block", str(e))

    return [
        notion_search,
        notion_get_page,
        notion_get_block_children,
        notion_create_page,
        notion_update_page_properties,
        notion_append_block_children,
        notion_query_database,
        notion_get_database_structure,
        notion_delete_block,
    ]