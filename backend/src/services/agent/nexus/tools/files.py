import json
from typing import Optional, Dict, List
from langchain_core.tools import tool, Tool
from .helpers import _clean_id, _parse_args, _parse_mcp_result, _run
from src.services.mcps.client.client_manager import MCPClientManager
from src.services.agent.common.mcp_errors import mcp_offline_error, mcp_no_client
from langgraph.errors import NodeInterrupt
from src.services.agent.Koda.tools.hitl import is_paused, validate_path
from langchain_core.runnables import RunnableConfig

# Base de datos y Chat 
from src.database.models.models import Message

# ---- FILES MCP TOOLS ----
def build_files_tools(user_id: str, chat_id: Optional[str] = None, db_session=None):
    """
    Factory: genera las herramientas para interactuar con archivos locales (Files MCP).
    Versión limpia SIN HITL, ideal para Nexus y Jarvis.
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "files"

    def get_files():
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
    
    # --- FILES MCP TOOLS ---

    @tool
    def list_directory(directory_path: str = ".") -> str:
        """
        Lists all files and folders inside a specific directory.
        Use this to understand the project structure before taking actions.
        Input: directory_path (str)
        """
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files")
                
            result = _run(client.list_directory(directory_path=directory_path))
            _record_tool_usage("list_directory")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "list_directory", str(e))

    @tool
    def read_file(file_path: str) -> str:
        """
        Reads the full content of a local file in the workspace.
        ALWAYS use this to read 'AGENTS.md' or source code files before editing them.
        Input: file_path (str)
        """
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files")

            result = _run(client.read_file(file_path=file_path))
            _record_tool_usage("read_file")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "read_file", str(e))

    @tool
    def search_items(query: str, search_type: str = "all") -> str:
        """
        Searches recursively for files or folders matching a specific name inside the ENTIRE project.
        'search_type' can be 'file', 'dir', or 'all'.
        ALWAYS use this tool FIRST if you don't know the exact path of a folder or file!
        """
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files")

            result = _run(client.search_items(query=query, search_type=search_type))
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "search_items", str(e))

    @tool
    def set_workspace(new_absolute_path: str) -> str:
        """
        Changes the root working directory of the project.
        Use this when the user asks to work on a completely different project or path on their computer.
        Input must be an absolute path (e.g. 'C:/Users/Name/Projects/NewApp').
        """
        try:
            client = get_files()
            if not client: 
                return mcp_no_client("Files")
            
            result = _run(client.set_workspace(new_absolute_path=new_absolute_path))
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "set_workspace", str(e))

    @tool
    def get_directory_tree(directory_path: str = ".", max_depth: int = 3) -> str:
        """
        Generates a visual map (tree) of a folder and all its subfolders.
        ALWAYS use this tool FIRST when exploring a new folder to understand its structure instantly,
        instead of listing directories one by one.
        """
        try:
            client = get_files()
            if not client: 
                return mcp_no_client("Files")
            
            result = _run(client.get_tree(directory_path=directory_path, max_depth=max_depth))
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "get_directory_tree", str(e))

    @tool
    def write_file(file_path: str, content: str, config: RunnableConfig) -> str:
        """
        Creates a new file at the given path with the provided content.
        RESTRICTED: only paths under 'skills/' are allowed.
        Use ONLY for skill-download tasks: writing SKILL.md, assets/*, references/*
        downloaded from a GitHub repo into skills/{skill-name}/.
        Input: file_path (str), content (str)
        """            
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")

        if session_id and is_paused(session_id):
            raise NodeInterrupt(f"La sesión {session_id} ha sido pausada.")

        # 1. Path traversal — SIEMPRE
        path_check = validate_path(file_path)
        if not path_check.is_safe:
            return path_check.block_message()

        # 2. Restricción a skills/ — SIEMPRE
        normalized = file_path.replace("\\", "/").lstrip("./")
        if not normalized.startswith("skills/"):
            return (
                f"HITL_BLOCKED: '{file_path}' está fuera de skills/. "
                "Nexus solo puede escribir dentro de skills/."
            )

        # 3. Ejecutar directamente — sin hitl_guard de contenido
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files")
            
            result = _run(client.write_file(file_path=file_path, content=content))
            _record_tool_usage("write_file")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "write_file", str(e))
        
    @tool
    def list_skills_tool(_: str = "") -> str:
        """
        Lists all available skills found in the skills/ directory.
        Use this to discover what skills are installed in the system.
        """
        try:
            client = get_files()
            if not client:
                return mcp_offline_error("Files")
            
            result = _run(client.list_skills())
            _record_tool_usage("list_skills")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files", "list_skills_tool", str(e))
        
        

    return [
        list_directory,
        search_items,
        read_file,
        set_workspace,
        get_directory_tree,
        write_file,
        list_skills_tool
    ]