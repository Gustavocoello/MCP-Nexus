# src/services/rag/pipeline.py
from sqlalchemy.orm import Session
import uuid
from typing import Optional
from .chunker import DocumentChunker
from .embeddings import embedding_client
from .vector_store import VectorStore

class RAGPipeline:
    def __init__(self, db_session: Session):
        self.chunker = DocumentChunker()
        self.vector_store = VectorStore(db_session)
        self.embedding = embedding_client

    def ingest_document(self, user_id: uuid.UUID, text: str, metadata: dict, source: str = "documents", filename = ""):
        """1. Corta -> 2. Vectoriza en Google -> 3. Guarda en Postgres"""
        chunks = self.chunker.chunk_text(text, filename=filename)
        if not chunks:
            return 0
        
        # Ensure the source is saved in the metadata JSONB
        metadata["source"] = source    
        
        # Petición HTTPS en lote a Google Gemini
        vectors = self.embedding.generate_batch(chunks)
        
        # Guarda todo en Postgres
        self.vector_store.save_batch(user_id, chunks, vectors, metadata)
        
        return len(chunks)

    def retrieve_context(self, user_id: uuid.UUID, query: str, limit: int = 4, source: Optional[str] = "documents") -> str:
        """1. Vectoriza pregunta en Google -> 2. Busca en Postgres -> 3. Devuelve texto"""
        # Vectorizamos la pregunta
        query_vector = self.embedding.generate(query)
        
        # Buscamos en pgvector
        results = self.vector_store.search_similar(user_id, query_vector, limit, source=source)
        
        if not results:
            return ""
            
        # Damos formato para que Jarvis lo entienda fácilmente
        context_parts = [f"--- [Fuente: {doc.filename}] |  Source: {source}] ---\n{doc.content}" for doc in results]
        return "\n\n".join(context_parts)