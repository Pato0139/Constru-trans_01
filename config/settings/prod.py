from .base import *  # noqa: F401,F403
import os
from urllib.parse import urlparse

DEBUG = False
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

SECRET_KEY = os.getenv("SECRET_KEY", None)
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no está definida en producción")

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
    DATABASES = {
        "default": {
            "ENGINE": {
                "postgres": "django.db.backends.postgresql",
                "postgresql": "django.db.backends.postgresql",
                "mysql": "django.db.backends.mysql",
                "sqlite": "django.db.backends.sqlite3",
            }.get(u.scheme.replace("+psycopg2","").replace("+pymysql",""), "django.db.backends.sqlite3"),
            "NAME": u.path.lstrip("/") if u.scheme.startswith("sqlite") else (u.hostname and u.path.lstrip("/")),
            "USER": "" if u.scheme.startswith("sqlite") else (u.username or ""),
            "PASSWORD": "" if u.scheme.startswith("sqlite") else (u.password or ""),
            "HOST": "" if u.scheme.startswith("sqlite") else (u.hostname or ""),
            "PORT": "" if u.scheme.startswith("sqlite") else (str(u.port) if u.port else ""),
        }
    }
else:
    # fallback a variables individuales
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
            "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", ""),
            "PORT": os.getenv("DB_PORT", ""),
        }
    }

# Estáticos: WhiteNoise si está instalado
try:
    import whitenoise  # noqa: F401
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
except ImportError:
    pass
