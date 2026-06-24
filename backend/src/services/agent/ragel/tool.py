3 #src/services/agent/ragel/tools.py
import os
import json
import uuid
from langchain_core.tools import tool, Tool
from src.services.rag.pipeline import RAGPipeline
from src.services.rag.vector_store import VectorStore
from src.database.settings.connection import SessionLocal
from src.core.logging import get_logger

logger = get_logger("ragel_tools")

def internet_search_fallback(query: str) -> str:
    """
    Función interna que ejecuta la búsqueda en cascada (Fallback).
    Orden: 1. Tavily -> 2. Brave -> 3. DuckDuckGo.
    """
    
    # ==========================================
    # 1. PRIMER INTENTO: TAVILY 
    # ==========================================
    try:
        logger.info(f"[RAGEL SEARCH] Intentando Tavily API para: '{query}'")
        from langchain_community.tools.tavily_search import TavilySearchResults
        
        # max_results=3 para no gastar demasiados tokens de lectura
        tavily_tool = TavilySearchResults(max_results=3)
        result = tavily_tool.invoke({"query": query})
        
        if result:
            # Formateamos el resultado de Tavily a texto limpio
            formatted_result = "\n".join([f"- Fuente ({r['url']}): {r['content']}" for r in result])
            return f"[Fuente: Tavily Search]\n{formatted_result}"
            
    except Exception as e:
        logger.warning(f"[RAGEL SEARCH] Tavily falló ({str(e)}). Activando Fallback 1 (Brave)...")

    # ==========================================
    # 2. SEGUNDO INTENTO: BRAVE SEARCH (1k gratis)
    # ==========================================
    try:
        logger.info(f"[RAGEL SEARCH] Intentando Brave Search API para: '{query}'")
        from langchain_community.tools.brave_search.tool import BraveSearch
        
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            raise ValueError("BRAVE_API_KEY no encontrada en el .env")
            
        brave_tool = BraveSearch.from_api_key(api_key=api_key, search_kwargs={"count": 3})
        result = brave_tool.invoke(query)
        
        if result:
            return f"[Fuente: Brave Search]\n{result}"
            
    except Exception as e:
        logger.warning(f"[RAGEL SEARCH] Brave falló ({str(e)}). Activando Fallback 2 (DuckDuckGo)...")

    # ==========================================
    # 3. ÚLTIMO RECURSO: DUCKDUCKGO 
    # ==========================================
    try:
        logger.info(f"[RAGEL SEARCH] Intentando DuckDuckGo API para: '{query}'")
        from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
        
        ddg_wrapper = DuckDuckGoSearchAPIWrapper(max_results=3)
        result = ddg_wrapper.run(query)
        
        if result:
            return f"[Fuente: DuckDuckGo]\n{result}"
            
    except Exception as e:
        logger.error(f"[RAGEL SEARCH] Fallo crítico total en búsquedas: {str(e)}")
        return "ERROR: Ragel informa que todos los motores de búsqueda (Tavily, Brave, DDG) están caídos. No es posible buscar en Internet en este momento."

    return "No se encontraron resultados relevantes en internet."

def get_rag_tool(user_id: str, client_type: str = "web"):
    @tool
    def search_my_documents(query: str) -> str:
        """
        USE THIS TOOL WHEN THE USER ASKS ABOUT THEIR UPLOADED FILES.
        Search the user's personal documents: PDFs, Excel files, receipts,
        images, or any file they have previously uploaded.
        Do NOT use this for code or programming questions — use Koda for that.
        Input: the user's question as a natural language string.
        """
        try:
            user_uuid = uuid.UUID(str(user_id))
 
            with SessionLocal() as db_session:
                pipeline = RAGPipeline(db_session)
 
                # source="documents" — NUNCA toca el codebase de Koda
                context = pipeline.retrieve_context(
                    user_id = user_uuid,
                    query   = query,
                    limit   = 4,
                    source  = "documents",
                )
 
            if not context:
                return (
                    "No relevant information found in your documents for this query. "
                    "Make sure you have uploaded the file you are asking about."
                )
 
            return f"Information found in your documents:\n\n{context}"
 
        except Exception as e:
            logger.error(f"[RAGEL RAG] Error buscando documentos: {e}")
            return f"Error searching your documents: {str(e)}"
 
    return search_my_documents


# ==========================================
# EXPORTACIÓN DE LA HERRAMIENTA PARA RAGEL
# ==========================================
def build_ragel_tools(user_id: str,  client_type: str = "web") -> list:
    """
    Builds the research and investigation tools for Ragel.
    (user_id is kept for future auditing or personalized RAG databases).
    """
    tools = [
        Tool.from_function(
            func=internet_search_fallback,
            name="internet_search",
            description=(
                "USEFUL WHENEVER YOU NEED TO SEARCH THE INTERNET. "
                "Use this tool to research current events, live news, real-time facts, "
                "or any information you are not absolutely certain about. "
                "The Input MUST be strictly the search query string."
            )
        ),
        get_rag_tool(user_id=user_id, client_type=client_type)
        # Future tools:
        # read_pdf_document, query_vector_database, etc.
    ]
    return tools