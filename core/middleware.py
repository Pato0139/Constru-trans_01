from core.db_preference import PREF_AUTO, clear_db_preference, set_db_preference


class DatabasePreferenceMiddleware:
    """Aplica la preferencia de BD de la sesión (local / remota / auto)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        pref = request.COOKIES.get("bd_preferida")
        if not pref:
            pref = request.session.get("bd_preferida", PREF_AUTO)
        set_db_preference(pref)
        try:
            return self.get_response(request)
        finally:
            clear_db_preference()
