from django.shortcuts import redirect
from django.urls import reverse

from .services import get_current_installation

ALLOWED_VIEWS = {
    "license_expired",
    "usuarios:login",
    "inicio:inicio",
}


class LicenseEnforcementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/static/") or request.path.startswith("/media/"):
            return self.get_response(request)

        match = getattr(request, "resolver_match", None)
        if match and match.view_name in ALLOWED_VIEWS:
            return self.get_response(request)

        inst = get_current_installation()
        if inst and inst.status in {"expired", "revoked", "tampered"}:
            return redirect(reverse("license_expired"))

        return self.get_response(request)
