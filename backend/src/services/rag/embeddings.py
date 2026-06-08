import os
import warnings

# Apaga los molestos mensajes de deprecación de LangChain y Google
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", module="langchain_google_genai")
warnings.filterwarnings("ignore", module="langgraph")

from langchain_google_genai import GoogleGenerativeAIEmbeddings

class HTTPSEmbeddingService:
    def __init__(self):
        # Leemos tu llave específica
        api_key = os.getenv("AI_STUDIO_KEY")
        
        self.client = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=api_key
        )

    def generate(self, text: str) -> list[float]:
        """Genera vector para una sola consulta."""
        return self.client.embed_query(text)

    def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """Genera vectores en LOTE. Manda todos los chunks de golpe."""
        return self.client.embed_documents(texts)

# Instancia global lista para usarse
embedding_client = HTTPSEmbeddingService()