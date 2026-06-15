"""Settings para desarrollo local (cada compañero en su PC)."""
from .base import *  # noqa
from .base import env

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '*']
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]


INSTALLED_APPS += ['django_browser_reload'] 
MIDDLEWARE += ['django_browser_reload.middleware.BrowserReloadMiddleware']

# Cookies sin HTTPS en local
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

if not env('EMAIL_HOST_USER', default=''):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
