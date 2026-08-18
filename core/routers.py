from core.db_preference import get_db_preference, PREF_LOCAL, PREF_REMOTA
from core.utils import conexion_remota_disponible

# Apps de Django que SIEMPRE deben vivir en la BD default (local)
# para evitar conflictos de sesión entre bases de datos.
_APPS_LOCALES = {"sessions", "auth", "contenttypes", "admin"}


class EnrutadorInventario:
    def _elegir_bd(self):
        pref = get_db_preference()

        if pref == PREF_LOCAL:
            return "local"

        if pref == PREF_REMOTA and conexion_remota_disponible():
            return "remota"

        # PREF_AUTO o remota pedida pero no disponible -> fallback a local
        if conexion_remota_disponible():
            return "remota"
        return "local"

    def db_for_read(self, model, **hints):
        if model._meta.app_label in _APPS_LOCALES:
            return "default"
        return self._elegir_bd()

    def db_for_write(self, model, **hints):
        if model._meta.app_label in _APPS_LOCALES:
            return "default"
        return self._elegir_bd()

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == "default":
            return True
        if db == "local":
            return False
        if db == "remota":
            return True
        return False