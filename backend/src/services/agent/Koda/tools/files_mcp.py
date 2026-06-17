import uuid
import json 
import asyncio
from typing import List, Optional
from langchain_core.tools import tool, Tool
from langchain_core.runnables import RunnableConfig
from langgraph.errors import NodeInterrupt      

from .hitl import hitl_guard, is_paused
from .helpers import _run, _parse_mcp_result

from src.database.models.models import Message
from src.services.mcps.client.client_manager import MCPClientManager
from src.services.agent.common.mcp_errors import mcp_offline_error, mcp_no_client


# =======================================
#        TOOLS FILES MCP
# =======================================

def build_koda_files_tools_mcp(user_id: str, chat_id: Optional[str] = None, db_session=None):
    """
    Factory: generates the tools for Koda, including Sandbox, Scraper, 
    and the local Files MCP operations.
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "files"

    def get_files():
        return manager.get_client(provider_name)
    
    def _record_tool_usage(tool_name: str):
        """Guarda un registro en BD de la herramienta utilizada."""
        if not db_session or not chat_id:
            return
        
        mcp_context_str = json.dumps({
            "tool_used": tool_name,
            "provider": "koda_file"
        })
        
        mcp_msg = Message(chat_id=chat_id, role="mcp-tool", content=mcp_context_str)
        db_session.add(mcp_msg)
        db_session.commit()
    
    # --- FILES MCP TOOLS ---

    @tool
    def koda_list_directory_mcp(directory_path: str = ".") -> str:
        """
        Lists all files and folders inside a specific directory.
        Use this to understand the project structure before taking actions.
        Input: directory_path (str)
        """
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files_koda")
                
            result = _run(client.list_directory(directory_path=directory_path))
            _record_tool_usage("koda_list_directory")
            return _parse_mcp_result(result)
        except Exception as e:
            # Fase 4: Manejo de errores amigable para el LLM
            return mcp_offline_error("Files_koda", "list_directory", str(e))
    @tool
    def koda_search_items_mcp(query: str, search_type: str = "all") -> str:
        """
        Searches recursively for files or folders matching a specific name inside the ENTIRE project.
        'search_type' can be 'file', 'dir', or 'all'.
        ALWAYS use this tool FIRST if you don't know the exact path of a folder or file!
        """
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files_koda")

            result = _run(client.search_items(query=query, search_type=search_type))
            _record_tool_usage("koda_search_items")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files_koda", "search_items", str(e))

    @tool
    def koda_read_file_mcp(file_path: str) -> str:
        """
        Reads the full content of a local file in the workspace.
        ALWAYS use this to read 'AGENTS.md' or source code files before editing them.
        Input: file_path (str)
        """
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files_koda")

            result = _run(client.read_file(file_path=file_path))
            _record_tool_usage("koda_read_file")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files_koda", "read_file", str(e))

    @tool
    def koda_patch_file_mcp(file_path: str, search_block: str, replace_block: str, config: RunnableConfig) -> str:
        """
        EDIT existing files surgically without rewriting the entire document.
        'search_block' MUST perfectly match the existing code.
        """
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        # 1. Verificar si está pausada
        if session_id and is_paused(session_id):
            raise NodeInterrupt(f"La sesión {session_id} ha sido pausada.")

        # 2. Guardián HITL (evaluamos el bloque de código nuevo que quiere inyectar)
        guard_msg = hitl_guard(
            text=replace_block,
            tool_name="koda_patch_file",
            user_id=user_id, # user_id viene del scope padre de la factory
            session_id=session_id
        )

        if guard_msg:
            if "HITL_BLOCKED" in guard_msg:
                return guard_msg
            if "HITL_REQUIRES_APPROVAL" in guard_msg:
                raise NodeInterrupt(guard_msg)

        # 3. Ejecución
        try:
            client = get_files()
            if not client:
                return mcp_no_client("Files_koda")

            result = _run(client.patch_file(
                file_path=file_path, 
                search_block=search_block, 
                replace_block=replace_block
            ))
            _record_tool_usage("koda_patch_file")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files_koda", "patch_file", str(e))
        
    @tool
    def set_workspace_mcp(new_absolute_path: str) -> str:
        """
        Changes the root working directory of the project.
        Use this when the user asks to work on a completely different project or path on their computer.
        Input must be an absolute path (e.g. 'C:/Users/Name/Projects/NewApp').
        """
        try:
            client = get_files()
            if not client: return mcp_no_client("Files_koda")
            result = _run(client.set_workspace(new_absolute_path=new_absolute_path))
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files_koda", "set_workspace", str(e))

    @tool
    def get_directory_tree_mcp(directory_path: str = ".", max_depth: int = 3) -> str:
        """
        Generates a visual map (tree) of a folder and all its subfolders.
        ALWAYS use this tool FIRST when exploring a new folder to understand its structure instantly,
        instead of listing directories one by one.
        """
        try:
            client = get_files()
            if not client: return "Error: Server offline."
            result = _run(client.get_tree(directory_path=directory_path, max_depth=max_depth))
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files_koda", "get_tree", str(e))
        
    @tool
    def koda_write_file_mcp(file_path: str, content: str, config: RunnableConfig) -> str:
        """
        [MCP FALLBACK] Creates a new file at the given path with the provided content.
        Use ONLY if the native koda_write_file tool fails.
        """            
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        user_id = configurable.get("user_id")

        if session_id and is_paused(session_id):
            raise NodeInterrupt(f"La sesión {session_id} ha sido pausada.")

        # Restricción a skills/ (Mantenida como solicitaste)
        normalized = file_path.replace("\\", "/").lstrip("./")
        if not normalized.startswith("skills/"):
            return (
                f"HITL_BLOCKED: '{file_path}' está fuera de skills/. "
                "Esta herramienta MCP solo puede escribir dentro de skills/."
            )

        try:
            client = get_files()
            if not client: return mcp_no_client("Files_koda_mcp")
            
            result = _run(client.write_file(file_path=file_path, content=content))
            _record_tool_usage("koda_write_file_mcp")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files_koda_mcp", "write_file", str(e))
        
    @tool
    def koda_list_skills_tool_mcp(_: str = "") -> str:
        """
        [MCP FALLBACK] Lists all available skills found in the skills/ directory.
        Use this to discover what skills are installed in the system.
        """
        try:
            client = get_files()
            if not client: return mcp_offline_error("Files_koda_mcp")
            
            result = _run(client.list_skills())
            _record_tool_usage("koda_list_skills_tool_mcp")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("Files_koda_mcp", "list_skills", str(e))

    return [
        koda_list_directory_mcp,
        koda_search_items_mcp,
        koda_read_file_mcp,
        koda_patch_file_mcp,
        set_workspace_mcp,
        get_directory_tree_mcp,
        koda_write_file_mcp,
        koda_list_skills_tool_mcp
    ]