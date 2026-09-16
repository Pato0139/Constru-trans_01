"""Memoria portable de pares pregunta/respuesta destilados."""
import hashlib
import json
import logging
import os
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)
DISTIL_DIR = Path(os.getenv("DISTIL_DIR", "ia/training/distil"))
DISTIL_JSONL = DISTIL_DIR / "qa_destiladas.jsonl"
VISTOS_JSON = DISTIL_DIR / "vistos.json"
COLECCION = "constru_trans_destilada"
MEMORIA_DISTANCIA_MAX = float(os.getenv("MEMORIA_DISTANCIA_MAX", "0.6"))
MEMORIA_RATIO_MIN = float(os.getenv("MEMORIA_RATIO_MIN", "0.72"))


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ\s]", " ", texto)).strip()


def hash_pregunta(pregunta: str) -> str:
    return hashlib.sha1(normalizar(pregunta).encode("utf-8")).hexdigest()


def _cargar_vistos() -> set:
    try:
        return set(json.loads(VISTOS_JSON.read_text(encoding="utf-8")))
    except Exception:
        return set()


def _guardar_vistos(vistos: set):
    DISTIL_DIR.mkdir(parents=True, exist_ok=True)
    VISTOS_JSON.write_text(json.dumps(sorted(vistos), ensure_ascii=False), encoding="utf-8")


def leer_pares() -> list:
    if not DISTIL_JSONL.exists():
        return []
    pares = []
    for linea in DISTIL_JSONL.read_text(encoding="utf-8").splitlines():
        try:
            if linea.strip():
                pares.append(json.loads(linea))
        except json.JSONDecodeError:
            continue
    return pares


def guardar_par(pregunta: str, respuesta: str, fuente: str, metadata: dict | None = None) -> dict:
    registro = {"id": hash_pregunta(pregunta), "pregunta": pregunta.strip(), "respuesta": respuesta.strip(), "fuente": fuente, "metadata": metadata or {}}
    DISTIL_DIR.mkdir(parents=True, exist_ok=True)
    with DISTIL_JSONL.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    vistos = _cargar_vistos()
    vistos.add(registro["id"])
    _guardar_vistos(vistos)
    return registro


def indexar_par(registro: dict) -> bool:
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        return False
    try:
        model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        client = chromadb.PersistentClient(path=str(DISTIL_DIR / "chroma"))
        embeddings = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model)
        collection = client.get_or_create_collection(COLECCION, embedding_function=embeddings)
        collection.upsert(
            ids=[registro["id"]],
            documents=[f"{registro['pregunta']}\n{registro['respuesta']}"],
            metadatas=[{"fuente": registro["fuente"]}],
        )
        return True
    except Exception:
        logger.exception("No se pudo indexar el par en Chroma")
        return False


def reindexar_desde_jsonl() -> int:
    return sum(indexar_par(par) for par in leer_pares())


def buscar_en_memoria(pregunta: str) -> str:
    resultado = _buscar_chroma(pregunta)
    if resultado:
        return resultado
    objetivo = normalizar(pregunta)
    mejor = (0.0, "")
    for par in leer_pares():
        ratio = SequenceMatcher(None, objetivo, normalizar(par.get("pregunta", ""))).ratio()
        if ratio > mejor[0]:
            mejor = (ratio, par.get("respuesta", ""))
    return mejor[1] if mejor[0] >= MEMORIA_RATIO_MIN else ""


def _buscar_chroma(pregunta: str) -> str:
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        client = chromadb.PersistentClient(path=str(DISTIL_DIR / "chroma"))
        embeddings = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model)
        collection = client.get_or_create_collection(COLECCION, embedding_function=embeddings)
        if collection.count() == 0:
            return ""
        result = collection.query(query_texts=[pregunta], n_results=1)
        docs = result.get("documents", [[]])[0]
        distances = result.get("distances", [[]])[0]
        if docs and distances and distances[0] <= MEMORIA_DISTANCIA_MAX:
            return docs[0].split("\n", 1)[-1].strip()
    except Exception:
        logger.exception("Búsqueda Chroma falló")
    return ""
