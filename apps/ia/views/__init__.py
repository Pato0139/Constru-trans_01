
from django.shortcuts import render, redirect
from django.http import JsonResponse
from ..services import preguntar_ia
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def chat_ia(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            mensaje = data.get("mensaje", "")
            historial = data.get("historial", [])
            respuesta = preguntar_ia(mensaje, request.user, historial)
            return JsonResponse({"respuesta": respuesta, "status": "ok"})
        except Exception as e:
            return JsonResponse({"respuesta": f"Lo siento, ocurrió un error: {str(e)}", "status": "error"})
    
    # Si es GET, redirigir al dashboard o inicio
    return redirect("inicio")

