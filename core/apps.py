from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from django.db.backends.signals import connection_created
        from django.dispatch import receiver

        @receiver(connection_created, weak=False)
        def set_statement_timeout_remota(sender, connection, **kwargs):
            """
            Neon pooled no acepta `-c statement_timeout=N` como startup param
            (error: unsupported startup parameter in options).

            Como alternativa, hacemos SET SESSION en la primera conexión a 'remota'
            una vez establecida, para cancelar queries que duren más de 5 segundos.
            """
            if connection.alias != "remota":
                return
            if connection.vendor != "postgresql":
                return
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET SESSION statement_timeout = 5000")
            except Exception:
                # Neon no permite statement_timeout en la sesión? no colgarse
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(
                    "No se pudo fijar statement_timeout en remota; continuando sin él."
                )
