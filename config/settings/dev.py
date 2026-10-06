from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Email: se imprime en consola en desarrollo
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CACHES más simple (para dev, sin Redis si lo hubiera en base)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "constru-trans-dev",
    }
}
