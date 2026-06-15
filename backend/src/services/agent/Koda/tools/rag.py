import uuid
import json 
import asyncio
from typing import List, Optional
from langchain_core.tools import tool, Tool
from src.services.rag.pipeline import RAGPipeline
from src.database.settings.connection import SessionLocal

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
                    filename = filename,
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