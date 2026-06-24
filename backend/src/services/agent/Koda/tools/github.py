import uuid
import json 
import asyncio
from typing import List, Optional
from langchain_core.tools import tool, Tool
from langchain_core.runnables import RunnableConfig     
from langgraph.types import interrupt
from ..security.hitl import hitl_guard

from src.database.models.models import Message
from src.services.mcps.client.client_manager import MCPClientManager
from src.services.agent.common.utils.session_manager import is_paused
from src.services.agent.common.helpers import mcp_offline_error, mcp_no_client, _run, _parse_mcp_result

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
            raise interrupt(f"La sesión {session_id} ha sido pausada.")

        guard_msg = hitl_guard(
            text=f"GitHub: Create branch '{ref}' on {owner}/{repo}",
            tool_name="koda_github_create_branch",
            user_id=user_id,
            session_id=session_id
        )
        if guard_msg:
            if "HITL_BLOCKED" in guard_msg: return guard_msg
            if "HITL_REQUIRES_APPROVAL" in guard_msg: raise interrupt(guard_msg)

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
            raise interrupt(f"La sesión {session_id} ha sido pausada.")

        guard_msg = hitl_guard(
            text=f"GitHub: Commit to '{path}' on branch '{branch}'\nMessage: {message}",
            tool_name="koda_github_create_or_update_file",
            user_id=user_id,
            session_id=session_id
        )
        if guard_msg:
            if "HITL_BLOCKED" in guard_msg: return guard_msg
            if "HITL_REQUIRES_APPROVAL" in guard_msg: raise interrupt(guard_msg)

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
            raise interrupt(f"La sesión {session_id} ha sido pausada.")

        guard_msg = hitl_guard(
            text=f"GitHub: Create Pull Request '{title}' ({head} -> {base})",
            tool_name="koda_github_create_pull_request",
            user_id=user_id,
            session_id=session_id
        )
        if guard_msg:
            if "HITL_BLOCKED" in guard_msg: return guard_msg
            if "HITL_REQUIRES_APPROVAL" in guard_msg: raise interrupt(guard_msg)

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

# --- TOOLS adicionales para Github MCP 
    @tool
    def koda_github_list_directory(owner: str, repo: str, path: str, branch: Optional[str] = "main") -> str:
        """
        Lists ALL files inside a GitHub directory recursively.
        ALWAYS use this FIRST to know which files to download from a repository folder.
        Returns a flat JSON list with the exact paths of all files (including those in subfolders).
        Input: owner (str), repo (str), path (str), branch (Optional[str])
        """
        try:
            client = get_github()
            if not client:
                return mcp_no_client("GitHub")

            def fetch_dir(current_path: str) -> list:
                all_files = []
                # Llamada usando tu sistema actual (_run)
                result = _run(client.github_get_file_contents(owner, repo, current_path, branch))
                
                # Usamos tu parseador para sacar el string de respuesta
                content_text = _parse_mcp_result(result)
                
                try:
                    items = json.loads(content_text)
                except Exception as parse_err:
                    print(f"Error parsing JSON from GitHub MCP: {parse_err}")
                    return all_files
                
                # Si la ruta era un archivo único, devuelve dict. Si era carpeta, devuelve lista.
                if isinstance(items, dict):
                    items = [items]
                    
                for item in items:
                    if item.get("type") == "file":
                        all_files.append(item["path"])
                    elif item.get("type") == "dir":
                        # ¡Recursividad! Llama a fetch_dir de nuevo para la subcarpeta
                        sub_files = fetch_dir(item["path"])
                        all_files.extend(sub_files)
                        
                return all_files

            # Iniciamos la recursividad desde el path original
            final_files_list = fetch_dir(path)
            
            _record_tool_usage("github_list_directory")
            
            # Devolvemos la lista en formato JSON (string) para que LangGraph/LLM lo lea fácil
            return json.dumps(final_files_list)
            
        except Exception as e:
            return mcp_offline_error("GitHub", "github_list_directory", str(e))
        
    @tool
    def koda_download_external_skill(owner: str, repo: str, path: str, branch: Optional[str] = "main") -> str:
        """
        Downloads a skill directory directly from a GitHub repository and saves it locally.
        ALWAYS use this tool to download or install a skill.
        Input: owner (str), repo (str), path (str), branch (Optional[str])
        """
        try:
            import base64
            gh_client = get_github()
            if not gh_client:
                return mcp_no_client("Github")
            
            # Importamos el manager del MCP FILES
            files_client = manager.get_client("files")
            if not files_client:
                return mcp_no_client("Files")

            # 1. Función recursiva para obtener paths
            def fetch_dir(current_path: str) -> list:
                all_files = []
                result = _run(gh_client.github_get_file_contents(owner, repo, current_path, branch))
                content_text = _parse_mcp_result(result)
                try:
                    items = json.loads(content_text)
                    if isinstance(items, dict): items = [items]
                    for item in items:
                        if item.get("type") == "file":
                            all_files.append(item["path"])
                        elif item.get("type") == "dir":
                            all_files.extend(fetch_dir(item["path"]))
                except Exception:
                    pass
                return all_files

            # 2. Obtenemos la lista de archivos
            files_to_download = fetch_dir(path)
            if not files_to_download:
                return "Error: No se encontraron archivos en la ruta."
            
            print(f"\n Descargando {len(files_to_download)} archivos...")
            
            downloaded = []
            # 3. Python hace el trabajo pesado, rápido y sin truncar
            for file_path in files_to_download:
                print(f" -> Obteniendo: {file_path}")
                gh_res = _run(gh_client.github_get_file_contents(owner, repo, file_path, branch))
                file_content = _parse_mcp_result(gh_res)
                
                content_to_write = file_content
                # Decodificamos el base64 que devuelve GitHub
                try:
                    parsed_json = json.loads(file_content)
                    # A veces GitHub lo devuelve en un array
                    if isinstance(parsed_json, list):
                        parsed_json = parsed_json[0]
                        
                    if isinstance(parsed_json, dict) and "content" in parsed_json:
                        if parsed_json.get("encoding") == "base64":
                            raw_b64 = parsed_json["content"].replace('\n', '')
                            content_to_write = base64.b64decode(raw_b64).decode("utf-8")
                        else:
                            content_to_write = parsed_json["content"]
                except Exception as e:
                    pass 
                
                # Guardamos localmente
                _run(files_client.write_file(file_path=file_path, content=content_to_write))
                downloaded.append(file_path)

            _record_tool_usage("download_external_skill")
            return f"EXITO: Se descargaron correctamente los archivos: {', '.join(downloaded)}"

        except Exception as e:
            return f"ERROR descargando skill: {str(e)}"   
        
    return [
        koda_github_search_repositories,
        koda_github_search_code,
        koda_github_get_file_contents,
        koda_github_get_issue,
        koda_github_get_branch_sha,
        koda_github_create_branch,
        koda_github_create_or_update_file,
        koda_github_create_pull_request,
        koda_github_list_directory,
        koda_download_external_skill
    ]