# Semantic memory is now handled by the AI Service
# These functions are kept for backward compatibility but are no-ops

def guardar_interaccion(doc_id: str, texto: str, metadata: dict):
    # Memory is now handled by the AI Service
    pass


def buscar_memoria(query: str, n_results: int = 3):
    # Memory is now handled by the AI Service
    return []
