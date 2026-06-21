import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"


def build_http_session():
    session = requests.Session()
    retries = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


HTTP_SESSION = build_http_session()


def verificar_conexion_ollama():
    try:
        response = HTTP_SESSION.get(f"{OLLAMA_URL}/api/tags", timeout=(2, 5))
        return response.status_code == 200
    except Exception:
        logger.exception("Error verificando conexión con Ollama")
        return False


def construir_prompt_sistema(contexto, nombre_usuario):
    contexto_texto = "\n".join(f"- {k}: {v}" for k, v in contexto.items() if k != "generated_at")

    return f"""
Eres el asistente virtual oficial de Constru-Trans.

Reglas:
1. Responde siempre en español.
2. Sé preciso, útil y profesional.
3. No inventes datos del sistema.
4. Si te preguntan por matemáticas, resuelve paso a paso.
5. Si te preguntan por el sistema, usa el contexto.
6. Si no sabes algo, dilo claramente.
7. Si la pregunta depende de datos del sistema y esos datos no están en el contexto, di que no tienes ese dato exacto ahora mismo.

Usuario actual: {nombre_usuario or "No identificado"}

Datos actuales del sistema:
{contexto_texto}
""".strip()


def preguntar_ollama(mensaje, contexto, nombre_usuario, historial):
    system_prompt = construir_prompt_sistema(contexto, nombre_usuario)

    messages = [{"role": "system", "content": system_prompt}]

    for msg in (historial or [])[-12:]:
        role = "user" if msg.get("sender") == "user" else "assistant"
        text = (msg.get("text") or "").strip()
        if text:
            messages.append({"role": role, "content": text[:1200]})

    messages.append({"role": "user", "content": mensaje[:3000]})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.4,
            "num_predict": 1200,
        },
    }

    try:
        response = HTTP_SESSION.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=(3, 90),
        )
        response.raise_for_status()
        data = response.json()
        respuesta = ((data.get("message") or {}).get("content") or "").strip()
        return respuesta if respuesta else None
    except Exception:
        logger.exception("Error consultando Ollama")
        return None
