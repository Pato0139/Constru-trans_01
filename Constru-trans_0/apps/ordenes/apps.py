from django.apps import AppConfig


class OrdenesConfig(AppConfig):
    name = 'apps.ordenes'

    def ready(self):
        import apps.ordenes.signals
