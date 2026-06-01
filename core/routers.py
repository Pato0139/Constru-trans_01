"""
Router de bases de datos para modo híbrido offline-first.

- Por defecto todo se guarda en 'default' (SQLite local) → funciona OFFLINE.
- Si hay conexión a 'remota' (Neon), las apps marcadas como APPS_NUBE
  leen/escriben directamente en la nube → sincronización entre compañeros.
- Las migraciones SIEMPRE se aplican en 'default' (SQLite local).
"""
from core.utils import conexion_remota_disponible


class EnrutadorInventario:
    """
    Apps críticas que se centralizan en la nube cuando hay conexión.
    Si la nube no está disponible, todo opera en local automáticamente.
    """

    # Apps que se centralizan en la nube para multidispositivo
    APPS_NUBE = [
        'auth', 'usuarios', 'sessions', 'admin',
        'historial', 'clientes',
    ]

    def db_for_read(self, model, **hints):
        """Lecturas: usa nube para APPS_NUBE si está disponible; si no, local."""
        if model._meta.app_label in self.APPS_NUBE and conexion_remota_disponible():
            return 'remota'
        return 'default'

    def db_for_write(self, model, **hints):
        """Escrituras: igual que lecturas."""
        if model._meta.app_label in self.APPS_NUBE and conexion_remota_disponible():
            return 'remota'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Permite relaciones entre default y remota."""
        db_list = ('default', 'remota')
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Las migraciones se aplican en todas las bases de datos (default y remota)."""
        return True
