import os
from urllib.parse import urlparse
os.environ.setdefault("SUPERADMIN_EMAIL", "edwardf5432@gmail.com")
os.environ.setdefault("SUPERADMIN_USERNAME", "Edward_Fonseca")
from .base import *  # noqa: F403

# ============================================================
# PROTECCIÓN ESTRICTA CONTRA EJECUCIÓN EN PRODUCCIÓN
# ============================================================
_PROD_HOST_FRAGMENT = "ep-fragrant-dew"

_raw_db_url = os.getenv("DATABASE_URL")
_test_db_url = os.getenv("TEST_DATABASE_URL")
_allowed_test_host = os.getenv("ALLOWED_TEST_DB_HOST")

# Validar DATABASE_URL contra producción
if _raw_db_url:
    _parsed_db = urlparse(_raw_db_url)
    if _PROD_HOST_FRAGMENT in (_parsed_db.hostname or ""):
        # En entorno de pruebas, no se permite usar la DATABASE_URL de producción directamente
        # a menos que TEST_DATABASE_URL esté explícitamente configurada y autorizada.
        pass

# Si se suministra TEST_DATABASE_URL, debe cumplir estrictamente las reglas
if _test_db_url:
    _u = urlparse(_test_db_url)
    _host = _u.hostname or ""
    
    # 1. Prohibir explícitamente el host de producción
    if _PROD_HOST_FRAGMENT in _host:
        raise RuntimeError(
            "FATAL - SEGURIDAD: TEST_DATABASE_URL apunta al host de producción ('"
            + _host[:12]
            + "...'). Las pruebas se abortan inmediatamente."
        )
    
    # 2. Exigir que ALLOWED_TEST_DB_HOST esté configurado y coincida exactamente
    if not _allowed_test_host:
        raise RuntimeError(
            "FATAL - SEGURIDAD: Para conectar pruebas a PostgreSQL externo se requiere definir la variable "
            "ALLOWED_TEST_DB_HOST con el host exacto permitido."
        )
    if _PROD_HOST_FRAGMENT in _allowed_test_host:
        raise RuntimeError(
            "FATAL - SEGURIDAD: ALLOWED_TEST_DB_HOST contiene el indicador de producción. Rechazado."
        )
    if _host != _allowed_test_host:
        raise RuntimeError(
            f"FATAL - SEGURIDAD: El host en TEST_DATABASE_URL ({_host[:12]}...) "
            f"no coincide con ALLOWED_TEST_DB_HOST ({_allowed_test_host[:12]}...)."
        )
        
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _u.path.lstrip("/"),
            "USER": _u.username or "",
            "PASSWORD": _u.password or "",
            "HOST": _u.hostname or "",
            "PORT": str(_u.port) if _u.port else "5432",
        }
    }
else:
    # Si DATABASE_URL es de producción y no hay TEST_DATABASE_URL, forzar SQLite seguro en memoria
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
        "local": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
        "remota": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
    }

ALLOWED_HOSTS = ["*", "testserver", "localhost", "127.0.0.1"]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# ============================================================
# PASSWORD HASHERS PARA PRUEBAS (ARGON2 REAL)
# ============================================================
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

SECURITY_MAX_WARNINGS = 999999

