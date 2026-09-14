import logging
import os

from openai import OpenAI
from httpx import Client

logger = logging.getLogger(__name__)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

client = (
    OpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        http_client=Client(timeout=30.0),
    )
    if LLM_API_KEY
    else None
)


def verificar_conexion_llm():
    if client is None:
        return False
    try:
        client.models.list()
        return True
    except Exception:
        logger.exception("No se pudo conectar al servidor LLM")
        return False


def construir_prompt_sistema(contexto, nombre_usuario, contexto_rag=""):
    contexto_texto = "\n".join(f"- {k}: {v}" for k, v in contexto.items() if k != "generated_at")
    rag_texto = f"\nDocumentos relevantes:\n{contexto_rag}" if contexto_rag else ""
    return f"""
Eres el asistente virtual oficial de Constru-Trans.

Reglas:
1. Responde siempre en español.
2. Sé preciso, útil y profesional.
3. No inventes datos del sistema.
4. Si faltan datos, dilo claramente.
5. Usa el contexto del sistema cuando aplique.
6. No inventes datos internos; si no aparecen en el contexto, dilo claramente.

Usuario actual: {nombre_usuario or "No identificado"}

Datos actuales del sistema:
{contexto_texto}
{rag_texto}
""".strip()


def preguntar_llm(mensaje, contexto, nombre_usuario, historial, contexto_rag=""):
    if client is None:
        logger.error("Cliente LLM no disponible: falta LLM_API_KEY")
        return None

    system_prompt = construir_prompt_sistema(contexto, nombre_usuario, contexto_rag)

    messages = [{"role": "system", "content": system_prompt}]

    for msg in (historial or [])[-12:]:
        role = "user" if msg.get("sender") == "user" or msg.get("role") == "user" else "assistant"
        text = (msg.get("text") or msg.get("content") or "").strip()
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
