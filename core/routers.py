class EnrutadorInventario:
    """
    Controla que las aplicaciones críticas se dirijan a la BD remota,
    mientras que el resto (usuarios, sesiones, etc.) se quedan localmente.
    """
    
    # Apps que queremos sincronizar con la nube
    APPS_REMOTAS = [
        'inventario', 'compras', 'ordenes', 'facturacion', 'pagos', 
        'clientes', 'transporte', 'usuarios', 'auth', 'sessions', 'admin',
        'historial'
    ]

    def _conexion_remota_disponible(self):
        """Verifica si la conexión remota está configurada y disponible."""
        import os
        from django.db import connections
        from django.db.utils import OperationalError, ConnectionDoesNotExist

        try:
            if 'remota' not in connections:
                return False
            if not os.getenv("DB_ENGINE") or not os.getenv("DB_PASSWORD"):
                return False
            connections['remota'].ensure_connection()
            return True
        except (OperationalError, ConnectionDoesNotExist, Exception):
            return False

    def db_for_read(self, model, **hints):
        """Lecturas: Intenta usar la nube para auth/sessions, si falla usa local."""
        if self._conexion_remota_disponible():
            # Apps que se centralizan en la nube para permitir login multidispositivo
            APPS_NUBE = ['auth', 'usuarios', 'sessions', 'admin', 'historial', 'clientes']
            if model._meta.app_label in APPS_NUBE:
                return 'remota'
        return 'default'

    def db_for_write(self, model, **hints):
        """Escrituras: Intenta usar la nube para auth/sessions/historial, si falla usa local."""
        if self._conexion_remota_disponible():
            # Apps que se centralizan en la nube para permitir login multidispositivo
            APPS_NUBE = ['auth', 'usuarios', 'sessions', 'admin', 'historial', 'clientes']
            if model._meta.app_label in APPS_NUBE:
                return 'remota'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Permite relaciones si ambos objetos están en la misma base de datos."""
        db_list = ('default', 'remota')
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Controla dónde se aplican las migraciones."""
        # Solo permitimos migraciones en la base local para simplificar
        return db == 'default'
