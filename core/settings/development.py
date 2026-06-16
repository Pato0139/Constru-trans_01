"""Settings para desarrollo local (cada compañero en su PC)."""

from .base import *  # noqa
from .base import env

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "*"]
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

# Hot reload
INSTALLED_APPS += ["django_browser_reload"]  # noqa
MIDDLEWARE += ["django_browser_reload.middleware.BrowserReloadMiddleware"]  # noqa

# Cookies sin HTTPS en local
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Si no hay credenciales SMTP, envía emails a consola (para probar password reset)
if not env("EMAIL_HOST_USER", default=""):
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
