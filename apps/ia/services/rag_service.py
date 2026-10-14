import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)
_collection = None
RAG_MAX_DISTANCE = float(os.getenv("RAG_MAX_DISTANCE", "0.75"))


def _get_collection():
    global _collection
    if os.getenv("RAG_ENABLED", "True").lower() not in {"1", "true", "yes"}:
        return None
    if _collection is not None:
        return _collection
    try:
        import chromadb
        path = Path(os.getenv("CHROMA_DIR", "media/chroma_constru_trans"))
        path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(path))
        _collection = client.get_or_create_collection("constru_trans_kb")
        return _collection
    except Exception:
        logger.exception("No se pudo inicializar RAG con ChromaDB")
        return None


def indexar_documentos(documentos):
    collection = _get_collection()
    if collection is None or not documentos:
        return 0
    collection.upsert(
        ids=[documento["id"] for documento in documentos],
        documents=[documento["texto"] for documento in documentos],
        metadatas=[documento.get("metadata", {}) for documento in documentos],
    )
    return len(documentos)


def buscar_contexto(query, k=3):
    collection = _get_collection()
    if collection is None or collection.count() == 0:
        return ""
    try:
        cantidad = min(k, collection.count())
        resultado = collection.query(query_texts=[query], n_results=cantidad)
        documentos = resultado.get("documents", [[]])[0]
        distancias = resultado.get("distances", [[]])[0]
        relevantes = [
            documento
            for documento, distancia in zip(documentos, distancias)
            if distancia is not None and distancia <= RAG_MAX_DISTANCE
        ]
        return "\n---\n".join(relevantes)
    except Exception:
        logger.exception("Error buscando contexto RAG")
        return ""
