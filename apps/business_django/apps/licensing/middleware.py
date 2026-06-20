
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse

from .services import get_current_installation

ALLOWED_VIEW_NAMES = {
    "licensing:license_expired",
    "licensing:license_activate",
    "usuarios:login",
    "usuarios:logout",
    "inicio:inicio",
}

ALLOWED_PATH_PREFIXES = (
    "/static/", "/media/", "/admin/", "/__reload__/", "/licensing/",
)


class LicenseEnforcementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(ALLOWED_PATH_PREFIXES):
            return self.get_response(request)

        match = getattr(request, "resolver_match", None)
        if match and match.view_name in ALLOWED_VIEW_NAMES:
            return self.get_response(request)

        try:
            inst = get_current_installation()
        except Exception:
            return self.get_response(request)

        if inst and inst.status in {"expired", "revoked", "tampered"}:
            try:
                return redirect(reverse("licensing:license_expired"))
            except NoReverseMatch:
                return redirect("/licensing/expired/")

        return self.get_response(request)
