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
        """Lecturas: Por defecto leemos de local para velocidad y offline-first."""
        return 'default'

    def db_for_write(self, model, **hints):
        """Escrituras: Intentamos local por defecto, el Celador se encarga de subirlo."""
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
