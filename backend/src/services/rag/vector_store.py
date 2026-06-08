# src/services/rag/vector_store.py
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.database.models import Document 
import uuid
from typing import Optional

class VectorStore:
    def __init__(self, db_session: Session):
        self.db = db_session

    def save_batch(self, user_id: uuid.UUID, chunks: list[str], vectors: list[float], metadata: dict):
        """Guarda cientos de chunks en la DB en un solo movimiento"""
        documents_to_insert = []
        
        for chunk, vector in zip(chunks, vectors):
            doc = Document(
                user_id=user_id,
                content=chunk,
                embedding=vector,
                filename=metadata.get("filename"),
                mime_type=metadata.get("mime_type"),
                file_size=metadata.get("file_size"),
                source=metadata.get("source", "upload") 
            )
            documents_to_insert.append(doc)
            
        self.db.bulk_save_objects(documents_to_insert)
        self.db.commit()

    def search_similar(self, user_id: uuid.UUID, query_vector: list[float], limit: int = 4, source: Optional[str] = None):
        """Búsqueda por distancia Coseno, filtrando por el ID del usuario y el source"""
        stmt = (
            select(Document)
            .filter(Document.user_id == user_id)
        )
        
        # Filtramos por source si se especifica (Ej: Solo código)
        if source:
            stmt = stmt.filter(Document.source == source)
            
        stmt = stmt.order_by(Document.embedding.cosine_distance(query_vector)).limit(limit)
        
        return self.db.execute(stmt).scalars().all()