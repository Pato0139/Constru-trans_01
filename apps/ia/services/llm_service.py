import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "local-key")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:latest")

client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def verificar_conexion_llm():
    try:
        client.models.list()
        return True
    except Exception:
        logger.exception("No se pudo conectar al servidor LLM")
        return False


def construir_prompt_sistema(contexto, nombre_usuario):
    contexto_texto = "\n".join(
        f"- {k}: {v}" for k, v in contexto.items()
        if k != "generated_at"
    )
    return f"""
Eres el asistente virtual oficial de Constru-Trans.

Reglas:
1. Responde siempre en español.
2. Sé preciso, útil y profesional.
3. No inventes datos del sistema.
4. Si faltan datos, dilo claramente.
5. Usa el contexto del sistema cuando aplique.

Usuario actual: {nombre_usuario or "No identificado"}

Datos actuales del sistema:
{contexto_texto}
""".strip()


def preguntar_llm(mensaje, contexto, nombre_usuario, historial):
    system_prompt = construir_prompt_sistema(contexto, nombre_usuario)

    messages = [{"role": "system", "content": system_prompt}]

    for msg in (historial or [])[-12:]:
        role = "user" if msg.get("sender") == "user" else "assistant"
        text = (msg.get("text") or "").strip()
        if text:
            messages.append({"role": role, "content": text[:1200]})

    messages.append({"role": "user", "content": mensaje[:3000]})

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.3
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception:
        logger.exception("Error consultando servidor LLM")
        return None
