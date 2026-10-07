from django.apps import AppConfig


class CatalogoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalogo"
    label = "catalogo"

    def ready(self):
        import apps.catalogo.signals  # noqa: F401
