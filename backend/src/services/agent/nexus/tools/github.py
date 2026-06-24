import json
from typing import Optional, Dict, List
from langchain_core.tools import tool, Tool
from .helpers import _clean_id, _parse_args, _parse_mcp_result, _run
from src.services.mcps.client.client_manager import MCPClientManager
from src.services.agent.common.helpers import mcp_offline_error, mcp_no_client


# Base de datos y Chat 
from src.database.models.models import Message


# --- GITHUB TOOLS ---    
def build_github_tools(user_id: str, chat_id: Optional[str] = None, db_session=None,  client_type: str = "web"):
    """
    Factory: Genera las herramientas de GitHub para Koda.
    Incluye protección HITL para acciones de escritura (ramas, commits, PRs).
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "github"

    def get_github():
        return manager.get_client("github")
    
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

    # --- 🟢 ACCIONES DE LECTURA (SAFE) ---

    @tool
    def github_search_repositories(query: str) -> str:
        """
        Searches GitHub for repositories matching the query.
        Input: query (str)
        """
        try: 
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")
            
            result = _run(client.github_search_repositories(query=query))
            _record_tool_usage("github_search_repositories")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("GitHub", "github_search_repositories", str(e))

    @tool
    def github_search_code(query: str) -> str:
        """
        Searches GitHub for specific code snippets across repositories.
        Useful to find examples of how a function is used in the wild.
        Input: query (str)
        """
        try: 
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")
            
            result = _run(client.github_search_code(query=query))
            _record_tool_usage("github_search_code")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("GitHub", "github_search_code", str(e))

    @tool
    def github_get_file_contents(owner: str, repo: str, path: str, branch: Optional[str] = None) -> str:
        """
        Reads the content of a file from a GitHub repository.
        Input: owner (str), repo (str), path (str), branch (Optional[str])
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")

            result = _run(client.github_get_file_contents(owner, repo, path, branch))
            _record_tool_usage("github_get_file_contents")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("GitHub", "github_get_file_contents", str(e))

    @tool
    def github_get_issue(owner: str, repo: str, issue_number: int) -> str:
        """
        Fetches the details of a specific GitHub issue to understand a bug or task.
        Input: owner (str), repo (str), issue_number (int)
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")

            result = _run(client.github_get_issue(owner, repo, issue_number))
            _record_tool_usage("github_get_issue")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("GitHub", "github_get_issue", str(e))

    @tool
    def github_get_branch_sha(owner: str, repo: str, branch: str = "main") -> str:
        """
        Gets the SHA hash of a branch.
        ALWAYS use this first when you need to create a new branch, as GitHub requires the base SHA.
        Input: owner (str), repo (str), branch (str)
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")
            
            result = _run(client.github_get_branch_sha(owner, repo, branch))
            _record_tool_usage("github_get_branch_sha")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error("GitHub", "github_get_branch_sha", str(e))     


    # --- 🔴 ACCIONES DE ESCRITURA (REQUIEREN HITL) *ONLY KODA* ---
    
    # --- TOOLS adicionales para Github MCP 
      
    
    return [
        github_search_repositories,
        github_search_code,
        github_get_file_contents,
        github_get_issue,
        github_get_branch_sha,
    ]