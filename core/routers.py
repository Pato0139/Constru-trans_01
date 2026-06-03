"""
Router de bases de datos para modo híbrido offline-first.

- Por defecto todo se guarda en 'default' (SQLite local) → funciona OFFLINE.
- Si hay conexión a 'remota' (Neon), las apps marcadas como APPS_NUBE
  leen/escriben directamente en la nube → sincronización entre compañeros.
- Las migraciones SIEMPRE se aplican en 'default' (SQLite local).
"""
from core.db_preference import debe_usar_bd_remota


class EnrutadorInventario:
    """
    Apps críticas que se centralizan en la nube cuando hay conexión.
    Si la nube no está disponible, todo opera en local automáticamente.
    """

    # Apps que se centralizan en la nube para multidispositivo.
    # sessions/admin/auth quedan en 'default' para no romper la cookie de sesión al cambiar de modo.
    APPS_NUBE = [
        'usuarios',
        'historial',
        'clientes',
    ]

    def db_for_read(self, model, **hints):
        """Lecturas: usa nube para APPS_NUBE si está disponible; si no, local."""
        if model._meta.app_label in self.APPS_NUBE and debe_usar_bd_remota():
            return 'remota'
        return 'default'

    def db_for_write(self, model, **hints):
        """Escrituras: igual que lecturas."""
        if model._meta.app_label in self.APPS_NUBE and debe_usar_bd_remota():
            return 'remota'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Permite relaciones entre default y remota."""
        db_list = ('default', 'remota')
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Las migraciones solo se aplican en 'default' (SQLite local)."""
        return db == 'default'
