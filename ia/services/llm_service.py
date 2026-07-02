import logging
import os

logger = logging.getLogger(__name__)

try:
    from httpx import Client
    from openai import OpenAI

    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "local-key")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:latest")

    # Crear cliente HTTP personalizado sin proxies
    http_client = Client()
    client = OpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        http_client=http_client
    )
except ImportError:
    client = None


def verificar_conexion_llm():
    if client is None:
        return False
    try:
        client.models.list()
        return True
    except Exception:
        logger.exception("No se pudo conectar al servidor LLM")
        return False


def construir_prompt_sistema(contexto, nombre_usuario):
    contexto_texto = "\n".join(f"- {k}: {v}" for k, v in contexto.items() if k != "generated_at")
    return f"""Eres el asistente virtual oficial de Constru-Trans.

Puedes responder dos tipos de preguntas:
1. Preguntas del sistema Constru-Trans (inventario, pedidos, compras, pagos, transporte, clientes, reportes).
2. Preguntas generales, triviales, educativas, conversacionales o cotidianas, aunque no tengan que ver con el sistema.

Reglas:
- Responde siempre en español.
- Si la pregunta usa datos del sistema, utiliza el contexto disponible.
- Si la pregunta NO usa datos del sistema, responde como un asistente general útil y natural.
- Si el usuario hace una continuación corta como "y en Bogotá", entiende que se refiere al tema anterior.
- No inventes datos internos del sistema.
- Para números grandes, usa punto como separador de miles y coma para decimales.
- Si algo no está claro, pide precisión sin responder de forma genérica vacía.

Usuario actual: {nombre_usuario or "No identificado"}

Datos actuales del sistema:
{contexto_texto}
""".strip()


def preguntar_llm(mensaje, contexto, nombre_usuario, historial):
    if client is None:
        logger.error("Cliente LLM no está disponible (openai no instalado)")
        return None

    system_prompt = construir_prompt_sistema(contexto, nombre_usuario)

    messages = [{"role": "system", "content": system_prompt}]

    for msg in (historial or [])[-12:]:
        role = "user" if msg.get("role") == "user" or msg.get("sender") == "user" else "assistant"
        text = (msg.get("content") or msg.get("text") or "").strip()
        if text:
            messages.append({"role": role, "content": text[:1200]})

    messages.append({"role": "user", "content": mensaje[:3000]})

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL, messages=messages, temperature=0.3
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception:
        logger.exception("Error consultando servidor LLM")
        return None
