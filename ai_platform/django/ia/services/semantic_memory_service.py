import logging
import os

logger = logging.getLogger(__name__)
_collection = None
_embedder = None


def _get_collection():
    global _collection, _embedder
    if _collection is not None:
        return _collection, _embedder
    if os.getenv("RAG_ENABLED", "True").lower() not in {"1", "true", "yes"}:
        return None, None
    try:
        import chromadb
        from chromadb.utils import embedding_functions

        path = os.getenv("CHROMA_DIR", "media/chroma_constru_trans")
        client = chromadb.PersistentClient(path=path)
        _embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=os.getenv(
                "EMBEDDING_MODEL",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            )
        )
        _collection = client.get_or_create_collection(
            "django_ia_memory", embedding_function=_embedder
        )
    except Exception:
        logger.exception("No se pudo inicializar la memoria semántica local")
        return None, None
    return _collection, _embedder


def guardar_interaccion(doc_id: str, texto: str, metadata: dict):
    collection, _ = _get_collection()
    if collection is None:
        return False
    collection.upsert(ids=[doc_id], documents=[texto], metadatas=[metadata])
    return True


def buscar_memoria(query: str, n_results: int = 3):
    collection, _ = _get_collection()
    if collection is None or collection.count() == 0:
        return []
    result = collection.query(query_texts=[query], n_results=min(n_results, collection.count()))
    return result.get("documents", [[]])[0]
