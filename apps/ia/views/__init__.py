import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from ..services import preguntar_ia, save_feedback

logger = logging.getLogger(__name__)


@login_required
@require_POST
def chat_ia(request):
    try:
        data = json.loads(request.body)
        mensaje = data.get("mensaje", "")
        historial = data.get("historial", [])
        session_id = data.get("session_id", None)

        respuesta, message_id = preguntar_ia(mensaje, request.user, historial, session_id)
        return JsonResponse({"respuesta": respuesta, "message_id": message_id, "status": "ok"})
    except json.JSONDecodeError:
        return JsonResponse(
            {"respuesta": "Formato de solicitud inválido.", "status": "error"},
            status=400,
        )
    except Exception:
        logger.exception("Error en chat_ia")
        return JsonResponse(
            {"respuesta": "Lo siento, ocurrió un error interno al procesar su solicitud.", "status": "error"},
            status=500,
        )


@login_required
@require_POST
def feedback_ia(request):
    try:
        data = json.loads(request.body)
        message_id = data.get("message_id")
        feedback = data.get("feedback")
        comment = data.get("comment", None)

        if not message_id or not feedback:
            return JsonResponse(
                {"success": False, "status": "error", "message": "Datos incompletos."},
                status=400,
            )

        success = save_feedback(message_id, feedback, comment, request.user)
        if not success:
            return JsonResponse(
                {"success": False, "status": "error", "message": "Mensaje no encontrado o no autorizado."},
                status=404,
            )
        return JsonResponse({"success": True, "status": "ok"})
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "status": "error", "message": "JSON inválido."},
            status=400,
        )
    except Exception:
        logger.exception("Error procesando feedback de IA")
        return JsonResponse(
            {"success": False, "status": "error", "message": "Error interno del servidor."},
            status=500,
        )
