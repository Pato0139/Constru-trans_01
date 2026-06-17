from core.db_preference import PREF_AUTO, PREF_REMOTA, clear_db_preference, set_db_preference
from core.utils import conexion_remota_disponible


class DatabasePreferenceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        pref = request.COOKIES.get('bd_preferida')
        if not pref:
            pref = request.session.get('bd_preferida', PREF_AUTO)
        
        # Si la preferencia es auto y la conexión remota está disponible, usar remoto
        if pref == PREF_AUTO and conexion_remota_disponible():
            pref = PREF_REMOTA
            
        set_db_preference(pref)
        try:
            return self.get_response(request)
        finally:
            clear_db_preference()
