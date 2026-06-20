import chromadb
from typing import List, Dict, Optional

from app.core.config import settings
from app.core.logging import logger
from app.memory.embeddings import embedding_service


class SemanticRetriever:
    """Semantic retrieval using ChromaDB"""

    def __init__(self):
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        self.collections = {}
        # Initialize default collections
        self._init_collections()
        logger.info("SemanticRetriever initialized with ChromaDB")

    def _init_collections(self):
        """Initialize default collections"""
        self.collections["conversation_memory"] = self.client.get_or_create_collection("conversation_memory")
        self.collections["user_facts"] = self.client.get_or_create_collection("user_facts")
        self.collections["company_knowledge"] = self.client.get_or_create_collection("company_knowledge")
        self.collections["document_chunks"] = self.client.get_or_create_collection("document_chunks")

    def add(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        embeddings: Optional[List[List[float]]] = None
    ):
        """Add documents to a collection"""
        collection = self.collections.get(collection_name)
        if not collection:
            collection = self.client.get_or_create_collection(collection_name)
            self.collections[collection_name] = collection

        # Generate embeddings if not provided
        if not embeddings:
            embeddings = embedding_service.embed_texts(documents)

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas if metadatas else [{} for _ in documents],
            embeddings=embeddings
        )
        logger.info(f"Added {len(documents)} items to {collection_name}")

    def search(
        self,
        collection_name: str,
        query_text: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        n_results: int = 5
    ) -> List[Dict]:
        """Search a collection"""
        collection = self.collections.get(collection_name)
        if not collection:
            logger.warning(f"Collection {collection_name} not found")
            return []

        if query_embedding is None and query_text is None:
            raise ValueError("Either query_text or query_embedding must be provided")

        if query_embedding is None:
            query_embedding = embedding_service.embed_text(query_text)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        # Format results
        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0.0
            })

        return formatted_results


# Singleton instance
semantic_retriever = SemanticRetriever()
