import logging
import os

import requests

logger = logging.getLogger(__name__)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001/api/v1/chat")
AI_INTERNAL_TOKEN = os.getenv("AI_INTERNAL_TOKEN", "super-internal-token")


def enviar_a_ai_service(
    mensaje: str,
    session_id: str,
    user_id: str | None,
    user_name: str | None,
    user_role: str | None,
    business_context: dict,
    historial: list | None = None,
    use_rag: bool = True,
):
    payload = {
        "message": mensaje,
        "session_id": session_id,
        "user_id": user_id,
        "user_name": user_name,
        "user_role": user_role,
        "business_context": business_context,
        "history": historial or [],
        "use_rag": use_rag,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Internal-Token": AI_INTERNAL_TOKEN,
    }

    try:
        response = requests.post(AI_SERVICE_URL, json=payload, headers=headers, timeout=90)
        response.raise_for_status()
        return response.json()
    except Exception:
        logger.exception("Error enviando solicitud al AI Service")
        return {
            "response": "No pude comunicarme con el servicio de IA en este momento.",
            "status": "error",
            "tool_calls": [],
        }
