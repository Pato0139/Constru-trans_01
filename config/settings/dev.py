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

# ------------------------------------------------------------
# Aislamiento de caché durante la ejecución de tests.
# LocMemCache es global al proceso: el contador de warnings de
# seguridad por IP (config/security.py) se filtraba entre tests y
# provocaba 403 por IP "bloqueada" en la suite (14 fallos).
# ------------------------------------------------------------
import sys as _sys

if "test" in _sys.argv or "pytest" in _sys.modules:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
