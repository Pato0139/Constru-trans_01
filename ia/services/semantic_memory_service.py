# Semantic memory is handled by the optional local RAG index.


def guardar_interaccion(doc_id: str, texto: str, metadata: dict):
    try:
        from .rag_service import indexar_documentos

        return indexar_documentos([{"id": doc_id, "texto": texto, "metadata": metadata}]) > 0
    except Exception:
        return False


def buscar_memoria(query: str, n_results: int = 3):
    try:
        from .rag_service import buscar_contexto

        contexto = buscar_contexto(query, k=n_results)
        return contexto.split("\n---\n") if contexto else []
    except Exception:
        return []
