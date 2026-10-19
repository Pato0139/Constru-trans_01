import os
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False

_raw_allowed = os.getenv("ALLOWED_HOSTS", "").strip()
if not _raw_allowed or _raw_allowed == "*" or any(h.strip() == "*" for h in _raw_allowed.split(",")):
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS debe estar definida explícitamente en producción y no puede contener comodín '*'."
    )
ALLOWED_HOSTS = [h.strip() for h in _raw_allowed.split(",") if h.strip()]

SECRET_KEY = os.getenv("SECRET_KEY", None)
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise ImproperlyConfigured("SECRET_KEY no está definida o es menor a 32 caracteres en producción.")

# Seguridad
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# BD desde DATABASE_URL o variables individuales
_db_url = os.getenv("DATABASE_URL")
if _db_url:
    u = urlparse(_db_url)
    if u.scheme.startswith("sqlite"):
        raise ImproperlyConfigured("SQLite no está permitido en el entorno de producción.")
    DATABASES = {
        "default": {
            "ENGINE": {
                "postgres": "django.db.backends.postgresql",
                "postgresql": "django.db.backends.postgresql",
                "mysql": "django.db.backends.mysql",
            }.get(
                u.scheme.replace("+psycopg2", "").replace("+pymysql", ""),
                "django.db.backends.postgresql",
            ),
            "NAME": u.path.lstrip("/"),
            "USER": u.username or "",
            "PASSWORD": u.password or "",
            "HOST": u.hostname or "",
            "PORT": str(u.port) if u.port else "",
        }
    }
else:
    # fallback a variables individuales
    db_engine = os.getenv("DB_ENGINE", "")
    db_name = os.getenv("DB_NAME", "")
    db_user = os.getenv("DB_USER", "")
    db_password = os.getenv("DB_PASSWORD", "")
    if not (db_name and db_user and db_password) or "sqlite" in db_engine.lower():
        raise ImproperlyConfigured(
            "Credenciales completas de base de datos de producción (PostgreSQL) son obligatorias."
        )
    DATABASES = {
        "default": {
            "ENGINE": db_engine or "django.db.backends.postgresql",
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": os.getenv("DB_HOST", ""),
            "PORT": os.getenv("DB_PORT", ""),
        }
    }

# Estáticos: WhiteNoise si está instalado
try:
    import whitenoise  # noqa: F401

    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
except ImportError:
    pass
