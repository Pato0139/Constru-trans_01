from django.apps import AppConfig


class ComprasConfig(AppConfig):
    name = 'apps.compras'

    def ready(self):
        import apps.compras.signals
