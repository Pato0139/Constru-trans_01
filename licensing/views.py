import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .services import validate_installation

logger = logging.getLogger(__name__)


def license_expired(request):
    return render(request, "licensing/expired.html")


@require_POST
@staff_member_required
def license_activate(request):
    try:
        payload = json.loads(request.body or "{}")
        inst = validate_installation()

        return JsonResponse({
            "status": inst.status,
            "expires_at": inst.expires_at.isoformat() if inst.expires_at else None,
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    except Exception:
        logger.exception("Error activando licencia")
        return JsonResponse({"error": "Error interno"}, status=500)
