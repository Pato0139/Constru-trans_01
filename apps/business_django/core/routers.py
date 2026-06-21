"""
Router de bases de datos para modo híbrido offline-first.
"""

from core.db_preference import debe_usar_bd_remota


class EnrutadorInventario:
    APPS_NUBE = [
        "usuarios",
        "historial",
        "clientes",
        "ia",  # Añadimos la app de IA para que use la misma BD
    ]

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.APPS_NUBE and debe_usar_bd_remota():
            return "remota"
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.APPS_NUBE and debe_usar_bd_remota():
            return "remota"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        db_list = ("default", "remota")
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == "remota":
            return app_label in self.APPS_NUBE
        return db == "default"
