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

# ---- MCPS GITHUB TOOLS (EN client_github.py) ----
def build_koda_github_tools(user_id: str, chat_id: Optional[str] = None, db_session=None):
    """
    Factory: Genera las herramientas de GitHub para Koda.
    Incluye protección HITL para acciones de escritura (ramas, commits, PRs).
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "koda_github"

    def get_github():
        return manager.get_client("github") # Aqui dejamos "github" porque asi esta en el manager
    
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

    # --- 🟢 ACCIONES DE LECTURA (SAFE) ---

    @tool
    def koda_github_search_repositories(query: str) -> str:
        """
        Searches GitHub for repositories matching the query.
        Input: query (str)
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client(provider_name)
            
            result = _run(client.github_search_repositories(query=query))
            _record_tool_usage("koda_github_search_repositories")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error(provider_name, "github_search_repositories", str(e))

    @tool
    def koda_github_search_code(query: str) -> str:
        """
        Searches GitHub for specific code snippets across repositories.
        Useful to find examples of how a function is used in the wild.
        Input: query (str)
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client(provider_name)
            
            result = _run(client.github_search_code(query=query))
            _record_tool_usage("koda_github_search_code")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error(provider_name, "github_search_code", str(e))

    @tool
    def koda_github_get_file_contents(owner: str, repo: str, path: str, branch: Optional[str] = None) -> str:
        """
        Reads the content of a file from a GitHub repository.
        Input: owner (str), repo (str), path (str), branch (Optional[str])
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client(provider_name)
            
            result = _run(client.github_get_file_contents(owner, repo, path, branch))
            _record_tool_usage("koda_github_get_file_contents")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error(provider_name, "github_get_file_contents", str(e))

    @tool
    def koda_github_get_issue(owner: str, repo: str, issue_number: int) -> str:
        """
        Fetches the details of a specific GitHub issue to understand a bug or task.
        Input: owner (str), repo (str), issue_number (int)
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client(provider_name)
            
            result = _run(client.github_get_issue(owner, repo, issue_number))
            _record_tool_usage("koda_github_get_issue")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error(provider_name, "github_get_issue", str(e))

    @tool
    def koda_github_get_branch_sha(owner: str, repo: str, branch: str = "main") -> str:
        """
        Gets the SHA hash of a branch.
        ALWAYS use this first when you need to create a new branch, as GitHub requires the base SHA.
        Input: owner (str), repo (str), branch (str)
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client(provider_name)
            
            result = _run(client.github_get_branch_sha(owner, repo, branch))
            _record_tool_usage("koda_github_get_branch_sha")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error(provider_name, "github_get_branch_sha", str(e))


    # --- 🔴 ACCIONES DE ESCRITURA (REQUIEREN HITL) ---

    @tool
    def koda_github_create_branch(owner: str, repo: str, ref: str, sha: str, config: RunnableConfig) -> str:
        """
        Creates a new branch in a GitHub repository.
        ref MUST be in the format 'refs/heads/branch-name'.
        sha MUST be the hash of the base commit (use koda_github_get_branch_sha first).
        """
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        if session_id and is_paused(session_id):
            raise NodeInterrupt(f"La sesión {session_id} ha sido pausada.")

        guard_msg = hitl_guard(
            text=f"GitHub: Create branch '{ref}' on {owner}/{repo}",
            tool_name="koda_github_create_branch",
            user_id=user_id,
            session_id=session_id
        )
        if guard_msg:
            if "HITL_BLOCKED" in guard_msg: return guard_msg
            if "HITL_REQUIRES_APPROVAL" in guard_msg: raise NodeInterrupt(guard_msg)

        try:
            client = get_github()
            if not client:
                return mcp_no_client(provider_name)
            
            result = _run(client.github_create_branch(owner, repo, ref, sha))
            _record_tool_usage("koda_github_create_branch")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error(provider_name, "github_create_branch", str(e))

    @tool
    def koda_github_create_or_update_file(owner: str, repo: str, path: str, content: str, message: str, branch: str, config: RunnableConfig, sha: Optional[str] = None) -> str:
        """
        Creates or updates a file in a GitHub repository (Commit).
        If updating an existing file, 'sha' is REQUIRED (the hash of the existing file).
        """
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        if session_id and is_paused(session_id):
            raise NodeInterrupt(f"La sesión {session_id} ha sido pausada.")

        guard_msg = hitl_guard(
            text=f"GitHub: Commit to '{path}' on branch '{branch}'\nMessage: {message}",
            tool_name="koda_github_create_or_update_file",
            user_id=user_id,
            session_id=session_id
        )
        if guard_msg:
            if "HITL_BLOCKED" in guard_msg: return guard_msg
            if "HITL_REQUIRES_APPROVAL" in guard_msg: raise NodeInterrupt(guard_msg)

        try:
            client = get_github()
            if not client:
                return mcp_no_client(provider_name)
            
            result = _run(client.github_create_or_update_file(owner, repo, path, content, message, branch, sha))
            _record_tool_usage("koda_github_create_or_update_file")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error(provider_name, "github_create_or_update_file", str(e))

    @tool
    def koda_github_create_pull_request(owner: str, repo: str, title: str, head: str, base: str, config: RunnableConfig, body: Optional[str] = None) -> str:
        """
        Opens a Pull Request in GitHub.
        head: The branch where your changes are (e.g., 'fix-bug')
        base: The branch you want to merge into (e.g., 'main')
        """
        configurable = config.get("configurable", {})
        session_id = configurable.get("session_id")
        
        if session_id and is_paused(session_id):
            raise NodeInterrupt(f"La sesión {session_id} ha sido pausada.")

        guard_msg = hitl_guard(
            text=f"GitHub: Create Pull Request '{title}' ({head} -> {base})",
            tool_name="koda_github_create_pull_request",
            user_id=user_id,
            session_id=session_id
        )
        if guard_msg:
            if "HITL_BLOCKED" in guard_msg: return guard_msg
            if "HITL_REQUIRES_APPROVAL" in guard_msg: raise NodeInterrupt(guard_msg)

        try:
            client = get_github()
            if not client:
                return mcp_no_client(provider_name)
            
            result = _run(client.github_create_pull_request(owner, repo, title, head, base, body))
            _record_tool_usage("koda_github_create_pull_request")
            return _parse_mcp_result(result)
        except Exception as e:
            return mcp_offline_error(provider_name, "github_create_pull_request", str(e))
        

# ----- TOOLS ADICIONALES AL MCP ------
        
    return [
        koda_github_search_repositories,
        koda_github_search_code,
        koda_github_get_file_contents,
        koda_github_get_issue,
        koda_github_get_branch_sha,
        koda_github_create_branch,
        koda_github_create_or_update_file,
        koda_github_create_pull_request
    ]