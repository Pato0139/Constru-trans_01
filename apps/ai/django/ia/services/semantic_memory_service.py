import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.HttpClient(host="localhost", port=8000)
collection = client.get_or_create_collection("django_ia_memory")
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def guardar_interaccion(doc_id: str, texto: str, metadata: dict):
    emb = embedder.encode([texto])[0].tolist()
    collection.add(
        ids=[doc_id],
        documents=[texto],
        embeddings=[emb],
        metadatas=[metadata]
    )


def buscar_memoria(query: str, n_results: int = 3):
    emb = embedder.encode([query])[0].tolist()
    result = collection.query(query_embeddings=[emb], n_results=n_results)
    return result.get("documents", [[]])[0]
