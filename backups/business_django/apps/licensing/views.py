import json
import os

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .services import activate_license


def license_expired(request):
    return render(request, "licensing/expired.html")


@csrf_exempt
def license_activate(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        customer_id = data.get("customer_id")
        days = data.get("days")
        secret = os.getenv("LICENSE_SECRET", "default-secret-key-change-this-in-production")
        provided_secret = data.get("secret")

        if provided_secret != secret:
            return JsonResponse({"error": "Invalid secret"}, status=403)
        if not customer_id or not days:
            return JsonResponse({"error": "Missing customer_id or days"}, status=400)

        inst = activate_license(customer_id, days)
        return JsonResponse(
            {
                "status": inst.status,
                "expires_at": inst.expires_at.isoformat() if inst.expires_at else None,
                "instance_id": str(inst.instance_id),
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
