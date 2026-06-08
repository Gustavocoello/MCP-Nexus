# src/services/agent/Koda/tools/tools.py
import uuid
import json 
import asyncio
from typing import Optional
from langchain_core.tools import tool, Tool
from langchain_core.runnables import RunnableConfig  #Para extraer session_id
from langgraph.errors import NodeInterrupt      

from .hitl import hitl_guard, is_paused
from .sandbox_client import execute_in_sandbox
from .web_scraper import scrape_technical_doc
from .ast_analyzer import get_code_skeleton
from src.services.rag.pipeline import RAGPipeline
from src.database.settings.connection import SessionLocal
from src.services.mcps.client.client_manager import MCPClientManager
from src.services.mcps.client.github.client_github import GithubMCPClient


@tool("koda_execute_code")
def koda_execute_code(command: str, config: RunnableConfig) -> str:
    """
    Use this tool to execute Bash scripts, Python, Node.js, or 
    install dependencies in an isolated Linux environment (16GB RAM Sandbox).
    ALWAYS use it to test your code before delivering it to the user.
    Example command: 'python test.py' or 'npm run build'.
    """
    # 1. Extraer el contexto inyectado por LangGraph
    configurable = config.get("configurable", {})
    session_id = configurable.get("session_id")
    user_id = configurable.get("user_id")

    # 2. Verificar si la sesión fue pausada manualmente por el Admin
    if session_id and is_paused(session_id):
        raise NodeInterrupt(f"La sesión {session_id} ha sido pausada. Esperando reanudación.")

    # 3. Pasar por el Guardián HITL
    if user_id:
        guard_msg = hitl_guard(
            text=command,
            tool_name="koda_execute_code",
            user_id=user_id,
            session_id=session_id
        )
        
        if guard_msg:
            if "HITL_BLOCKED" in guard_msg:
                # Koda no tiene permiso. Le devolvemos el error como string para que busque otra forma.
                return guard_msg 
            
            if "HITL_REQUIRES_APPROVAL" in guard_msg:
                # Riesgo medio: Detenemos la ejecución del grafo completamente.
                raise NodeInterrupt(guard_msg)

    # 4. Si todo está SAFE o ya fue aprobado, ejecutar:
    return execute_in_sandbox(command)

@tool("koda_read_technical_doc")
def koda_read_technical_doc(url: str) -> str:
    """
    Use this tool to READ official documentation, API references, or GitHub files.
    Provide the EXACT URL (e.g., 'https://react.dev/reference/react').
    It will scrape the website and return the text and code blocks.
    Always use this when working with unfamiliar or updated libraries.
    """
    return scrape_technical_doc(url)

@tool("koda_get_code_skeleton")
def koda_get_code_skeleton(file_path: str) -> str:
    """
    Use this tool to deeply analyze large source code files (.py, .js, .ts).
    It returns an Abstract Syntax Tree (AST) skeleton showing all classes, 
    functions, and their exact line numbers.
    ALWAYS use this before editing a massive file to understand its structure and save tokens.
    """
    return get_code_skeleton(file_path)

def get_koda_rag_tools(user_id: str):
    """
    Tools for Long-Term Memory (RAG Dev) isolated by user_id.
    """
    
    @tool("koda_memorize_file")
    def koda_memorize_file(filename: str, file_content: str) -> str:
        """
        Use this tool to save a source code file into your Long-Term Memory (Vector Database).
        Do this when you write a new important module or when the user asks you to 'learn' a file.
        Input: filename (str), file_content (str)
        """
        try:
            user_uuid = uuid.UUID(str(user_id))
 
            with SessionLocal() as db_session:
                pipeline = RAGPipeline(db_session)
 
                # Detecta el lenguaje para guardarlo en metadata
                language = pipeline.chunker.detect_language(filename)
 
                metadata = {
                    "filename": filename,
                    "source":   "codebase",     # filtra Koda vs documentos de usuario
                    "language": language,        # "python", "ts", "sql", etc.
                    "mime_type": "text/plain",
                }
 
                # ← filename se pasa al chunker para que detecte el lenguaje
                chunks_saved = pipeline.ingest_document(
                    user_id  = user_uuid,
                    text     = file_content,
                    metadata = metadata,
                    source   = "codebase",
                    filename = filename,         # ← nuevo parámetro (ver pipeline.py abajo)
                )
 
            return f"Success: Memorized '{filename}' ({language}) into {chunks_saved} semantic chunks."
 
        except Exception as e:
            return f"Error memorizing file: {str(e)}"
 
    @tool("koda_search_codebase")
    def koda_search_codebase(query: str) -> str:
        """
        Search the user's Long-Term Memory for previously written code, architectures, or patterns.
        Use this when asked to implement something similar to past work.
        Input: query (semantic search string, e.g., 'how does the auth middleware work?')
        """
        try:
            user_uuid = uuid.UUID(str(user_id))
 
            with SessionLocal() as db_session:
                pipeline = RAGPipeline(db_session)
 
                # Una línea — retrieve_context ya hace: embed → search → formatear
                # source="codebase" asegura que NO busca en PDFs del usuario
                context = pipeline.retrieve_context(
                    user_id = user_uuid,
                    query   = query,
                    limit   = 4,
                    source  = "codebase",   # mapea a source en vector_store
                )
 
            if not context:
                return "No existing code found for this query in the vector database."
 
            return f"Found relevant codebase examples in long-term memory:\n\n{context}"
 
        except Exception as e:
            return f"Error retrieving codebase memory: {str(e)}"
 
    return [koda_memorize_file, koda_search_codebase]

# =======================================
#        TOOLS FILES MCP
# =======================================

# ---------- HELPERS=------------------
def _run(coro):
    """Helper to run async code from synchronous LangChain tools."""
    import concurrent.futures
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run_in_thread)
        return future.result()

def _parse_mcp_result(result) -> str:
    """Extracts text from the MCP result and returns it as a string."""
    try:
        content = result.get("data", result)
        
        if isinstance(content, list):
            texts = []
            for item in content:
                if hasattr(item, "text"):
                    texts.append(item.text)
                elif isinstance(item, dict):
                    texts.append(json.dumps(item, ensure_ascii=False))
                else:
                    texts.append(str(item))
            return "\n".join(texts)
        
        if isinstance(content, str):
            return content
            
        return json.dumps(content, ensure_ascii=False)
    except Exception as e:
        return f"Error parsing result: {e}"

def build_koda_files_tools(user_id: str):
    """
    Factory: generates the tools for Koda, including Sandbox, Scraper, 
    and the local Files MCP operations.
    """
    manager = MCPClientManager(user_id=user_id)
    provider_name = "files"

    def get_files():
        return manager.get_client(provider_name)
    
    # --- FILES MCP TOOLS ---

    @tool
    def koda_list_directory(directory_path: str = ".") -> str:
        """
        Lists all files and folders inside a specific directory.
        Use this to understand the project structure before taking actions.
        Input: directory_path (str)
        """
        try:
            client = get_files()
            if not client:
                return "Error: The files MCP server is completely offline or not configured."
                
            result = _run(client.list_directory(directory_path=directory_path))
            return _parse_mcp_result(result)
        except Exception as e:
            # Fase 4: Manejo de errores amigable para el LLM
            return f"Error: Cannot list directory because the files server is offline or unreachable. Details: {str(e)}"

    @tool
    def koda_read_file(file_path: str) -> str:
        """
        Reads the full content of a local file in the workspace.
        ALWAYS use this to read 'AGENTS.md' or source code files before editing them.
        Input: file_path (str)
        """
        try:
            client = get_files()
            if not client:
                return "Error: The files MCP server is completely offline or not configured."

            result = _run(client.read_file(file_path=file_path))
            return _parse_mcp_result(result)
        except Exception as e:
            return f"Error: Cannot read file because the server is offline. Details: {str(e)}"

    @tool
    def koda_patch_file(file_path: str, search_block: str, replace_block: str, config: RunnableConfig) -> str:
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
                return "Error: The files MCP server is completely offline or not configured."

            result = _run(client.patch_file(
                file_path=file_path, 
                search_block=search_block, 
                replace_block=replace_block
            ))
            return _parse_mcp_result(result)
        except Exception as e:
            return f"Error: Cannot patch file because the server is offline. Details: {str(e)}"

    return [
        koda_list_directory,
        koda_read_file,
        koda_patch_file
    ]
    
    # ----- MCP CONTEXT7 TOOLS (EN client_context7.py) -----
    
def build_koda_context7_tools(user_id: str):
    """
    Factory: Obtiene dinámicamente las herramientas de documentación de Context7.
    Nota: Requiere ser ejecutado dentro de un contexto asíncrono para extraerlas,
    por lo que usamos el _run() síncrono para la fase de construcción.
    """
    manager = MCPClientManager(user_id=user_id)
    
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
    
    # ---- MCPS GITHUB TOOLS (EN client_github.py) ----
def build_koda_github_tools(user_id: str):
    """
    Factory: Genera las herramientas de GitHub para Koda.
    Incluye protección HITL para acciones de escritura (ramas, commits, PRs).
    """
    manager = MCPClientManager(user_id=user_id)

    def get_github():
        return manager.get_client("github")

    # --- 🟢 ACCIONES DE LECTURA (SAFE) ---

    @tool
    def koda_github_search_repositories(query: str) -> str:
        """
        Searches GitHub for repositories matching the query.
        Input: query (str)
        """
        try:
            client = get_github()
            result = _run(client.github_search_repositories(query=query))
            return _parse_mcp_result(result)
        except Exception as e:
            return f"Error: Cannot search repositories. {str(e)}"

    @tool
    def koda_github_search_code(query: str) -> str:
        """
        Searches GitHub for specific code snippets across repositories.
        Useful to find examples of how a function is used in the wild.
        Input: query (str)
        """
        try:
            client = get_github()
            result = _run(client.github_search_code(query=query))
            return _parse_mcp_result(result)
        except Exception as e:
            return f"Error: Cannot search code. {str(e)}"

    @tool
    def koda_github_get_file_contents(owner: str, repo: str, path: str, branch: Optional[str] = None) -> str:
        """
        Reads the content of a file from a GitHub repository.
        Input: owner (str), repo (str), path (str), branch (Optional[str])
        """
        try:
            client = get_github()
            result = _run(client.github_get_file_contents(owner, repo, path, branch))
            return _parse_mcp_result(result)
        except Exception as e:
            return f"Error: Cannot read file contents. {str(e)}"

    @tool
    def koda_github_get_issue(owner: str, repo: str, issue_number: int) -> str:
        """
        Fetches the details of a specific GitHub issue to understand a bug or task.
        Input: owner (str), repo (str), issue_number (int)
        """
        try:
            client = get_github()
            result = _run(client.github_get_issue(owner, repo, issue_number))
            return _parse_mcp_result(result)
        except Exception as e:
            return f"Error: Cannot fetch issue. {str(e)}"

    @tool
    def koda_github_get_branch_sha(owner: str, repo: str, branch: str = "main") -> str:
        """
        Gets the SHA hash of a branch.
        ALWAYS use this first when you need to create a new branch, as GitHub requires the base SHA.
        Input: owner (str), repo (str), branch (str)
        """
        try:
            client = get_github()
            result = _run(client.github_get_branch_sha(owner, repo, branch))
            return _parse_mcp_result(result)
        except Exception as e:
            return f"Error: Cannot get branch SHA. {str(e)}"


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
            result = _run(client.github_create_branch(owner, repo, ref, sha))
            return _parse_mcp_result(result)
        except Exception as e:
            return f"Error: Cannot create branch. {str(e)}"

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
            result = _run(client.github_create_or_update_file(owner, repo, path, content, message, branch, sha))
            return _parse_mcp_result(result)
        except Exception as e:
            return f"Error: Cannot commit file. {str(e)}"

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
            result = _run(client.github_create_pull_request(owner, repo, title, head, base, body))
            return _parse_mcp_result(result)
        except Exception as e:
            return f"Error: Cannot create Pull Request. {str(e)}"

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

# TOOLS TEMPLATE AGENT

def build_koda_tools(user_id: str):
    """Retorna la lista de herramientas disponibles para Koda."""
    return [
        koda_execute_code,
        koda_read_technical_doc,
        koda_get_code_skeleton,
        *get_koda_rag_tools(user_id),
        *build_koda_files_tools(user_id),
        *build_koda_github_tools(user_id),
        *build_koda_context7_tools(user_id)
    ]