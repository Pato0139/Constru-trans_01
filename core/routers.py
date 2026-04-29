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

    def db_for_read(self, model, **hints):
        """Lecturas: Intenta usar la nube para auth/sessions, si falla usa local."""
        import os
        from django.db import connections
        from django.db.utils import OperationalError

        # Apps que se centralizan en la nube para permitir login multidispositivo
        APPS_NUBE = ['auth', 'usuarios', 'sessions', 'admin', 'historial']

        if os.getenv("DB_PASSWORD") and model._meta.app_label in APPS_NUBE:
            try:
                # Verificamos conexión rápida solo si es necesario
                connections['remota'].ensure_connection()
                return 'remota'
            except OperationalError:
                # Si falla la nube (sin internet o mala clave), usamos la local sin morir
                return 'default'
        return 'default'

    def db_for_write(self, model, **hints):
        """Escrituras: Intenta usar la nube para auth/sessions/historial, si falla usa local."""
        import os
        from django.db import connections
        from django.db.utils import OperationalError

        # Apps que se centralizan en la nube para permitir login multidispositivo
        APPS_NUBE = ['auth', 'usuarios', 'sessions', 'admin', 'historial']

        if os.getenv("DB_PASSWORD") and model._meta.app_label in APPS_NUBE:
            try:
                connections['remota'].ensure_connection()
                return 'remota'
            except OperationalError:
                return 'default'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Permite relaciones si ambos objetos están en la misma base de datos."""
        db_list = ('default', 'remota')
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Controla dónde se aplican las migraciones."""
        import os
        # Si no hay credenciales de base de datos remota, solo permitimos migraciones en local
        if not os.getenv("DB_PASSWORD"):
            return db == 'default'

        if app_label in self.APPS_REMOTAS:
            return db == 'remota' or db == 'default'
        return db == 'default'
