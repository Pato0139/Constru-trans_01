from typing import List

from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.logging import logger


class EmbeddingService:
    """Service for generating text embeddings"""

    def __init__(self):
        self.model_name = settings.EMBEDDINGS_MODEL
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        logger.info("Embedding model loaded successfully")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        return self.model.encode(text, convert_to_numpy=True).tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        return self.model.encode(texts, convert_to_numpy=True).tolist()


# Singleton instance
embedding_service = EmbeddingService()
