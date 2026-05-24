import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .services import validate_installation


def license_expired(request):
    return render(request, "licensing/expired.html")


@csrf_exempt
def license_activate(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        inst = validate_installation()
        return JsonResponse({"status": inst.status, "expires_at": inst.expires_at.isoformat() if inst.expires_at else None})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
