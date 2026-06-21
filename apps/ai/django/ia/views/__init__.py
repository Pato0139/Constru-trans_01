import json

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from ..services import preguntar_ia, save_feedback


@csrf_exempt
def chat_ia(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            mensaje = data.get("mensaje", "")
            historial = data.get("historial", [])
            session_id = data.get("session_id", None)

            respuesta, message_id = preguntar_ia(mensaje, request.user, historial, session_id)
            return JsonResponse({"respuesta": respuesta, "message_id": message_id, "status": "ok"})
        except Exception as e:
            return JsonResponse(
                {"respuesta": f"Lo siento, ocurrió un error: {str(e)}", "status": "error"}
            )

    # Si es GET, redirigir al dashboard o inicio
    return redirect("inicio")


@csrf_exempt
def feedback_ia(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            message_id = data.get("message_id")
            feedback = data.get("feedback")
            comment = data.get("comment", None)

            success = save_feedback(message_id, feedback, comment, request.user)
            return JsonResponse({"success": success, "status": "ok"})
        except Exception as e:
            return JsonResponse({"success": False, "status": "error", "message": str(e)})

    return JsonResponse({"success": False, "status": "error"})
