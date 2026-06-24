# src/services/agent/Koda/tools/tools.py
import uuid
import json 
import asyncio
from typing import List, Optional
from langchain_core.tools import tool, Tool
from langchain_core.tools import StructuredTool
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt      

from .security.hitl import hitl_guard
from .tools.sandbox_client import execute_in_sandbox
from .tools.web_scraper import scrape_technical_doc
from .tools.ast_analyzer import get_code_skeleton
from .tools.github import build_koda_github_tools
from .tools.context7 import build_koda_context7_tools
from .tools.files import build_koda_files_tools
from .tools.devtools import build_devtools_tools
from .tools.rag import get_koda_rag_tools

from src.services.rag.pipeline import RAGPipeline
from src.database.settings.connection import SessionLocal
from src.services.agent.common.utils.session_manager import is_paused


@tool("koda_execute_code")
def koda_execute_code(command: str, config: RunnableConfig) -> str:
    """
    Use this tool to execute Bash scripts, Python, Node.js, or 
    install dependencies in an isolated Linux environment (8GB RAM Sandbox).
    ALWAYS use it to test your code before delivering it to the user.
    Example command: 'python test.py' or 'npm run build'.
    
    CRITICAL RULE: DO NOT use this tool to simply list directories, 
    read files, or find folders (like 'ls' or 'find'). For reading the 
    file system, ALWAYS use the 'Files MCP' tools instead. Only use this 
    Sandbox when you need to EXECUTE or COMPILE code.
    """
    # 1. Extraer el contexto inyectado por LangGraph
    configurable = config.get("configurable", {})
    session_id = configurable.get("session_id")
    user_id = configurable.get("user_id")

    # 2. Verificar si la sesión fue pausada manualmente por el Admin
    if session_id and is_paused(session_id):
        raise interrupt(f"La sesión {session_id} ha sido pausada. Esperando reanudación.")

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
                raise interrupt(guard_msg)

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

# TOOLS TEMPLATE AGENT

def build_koda_tools(user_id: str, client_type: str = "Web"):
    """Retorna la lista de herramientas disponibles para Koda."""
    
    base_tools = [
        koda_read_technical_doc,
        koda_get_code_skeleton,
        *get_koda_rag_tools(user_id),
        *build_koda_files_tools(user_id),
        *build_koda_github_tools(user_id),
        *build_koda_context7_tools(user_id),
        *build_devtools_tools(user_id)
    ]
    
    if client_type != "cli":
       base_tools.insert(0, koda_execute_code)

    return base_tools
    