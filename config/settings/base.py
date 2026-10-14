import os
from pathlib import Path

import dj_database_url
import environ

# ============================================================
# RUTAS Y ENV
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

DJANGO_ENV = os.getenv("DJANGO_ENV", "development").lower()

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    EMAIL_USE_TLS=(bool, True),
    EMAIL_USE_SSL=(bool, False),
    EMAIL_PORT=(int, 587),
    EMAIL_TIMEOUT=(int, 30),
    PASSWORD_RESET_TIMEOUT=(int, 1800),
    SESSION_COOKIE_AGE=(int, 1209600),
    USE_S3=(bool, False),
    LICENSE_REQUIRED=(bool, False),
    LICENSE_SERVER_URL=(str, ""),
    LICENSE_PUBLIC_KEY=(str, ""),
    LICENSE_HEARTBEAT_MINUTES=(int, 360),
    LICENSE_MAX_AGE_DAYS=(int, 30),
    OPENWEATHER_API_KEY=(str, ""),
)

environ.Env.read_env(BASE_DIR / ".env")

# ============================================================
# SEGURIDAD
# ============================================================


def get_secret_key():
    """Devuelve la SECRET_KEY de forma estable.

    - Producción: exige una clave real en el entorno o en .env.
    - Desarrollo: si falta o es inválida, genera una clave aleatoria y la
      PERSISTE en .env (no se regenera en cada inicio, así no se invalidan
      las sesiones al reiniciar runserver). Es lo que hacía el setup anterior,
      pero ahora la lógica vive aquí y nunca deja el proyecto sin arrancar.
    """
    secret_key = env("SECRET_KEY", default="").strip()
    default_secret_placeholders = {
        "cambia-esto-por-una-clave-aleatoria-de-50-caracteres",
        "cambiar",
        "change-me",
        "changeme",
        "secret-key",
        "example-secret-key",
    }
    placeholder_keys = {value.lower() for value in default_secret_placeholders}

    def is_valid_key(value):
        return bool(value) and len(value) >= 32 and value.lower() not in placeholder_keys

    if is_valid_key(secret_key):
        return secret_key

    env_file = BASE_DIR / ".env"

    # 1) En desarrollo, rescatar una clave válida directamente del .env
    if DJANGO_ENV != "production" and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() == "SECRET_KEY":
                dotenv_secret_key = value.strip().strip("\"'")
                if is_valid_key(dotenv_secret_key):
                    return dotenv_secret_key

    if DJANGO_ENV == "production":
        raise RuntimeError(
            "SECRET_KEY no configurada, demasiado corta o con valor por defecto. "
            "Define una clave fija de al menos 32 caracteres en el entorno o en .env."
        )

    # 2) Desarrollo sin clave: generarla y guardarla para que sea estable.
    try:
        from django.core.management.utils import get_random_secret_key

        generated = get_random_secret_key()
        with env_file.open("a", encoding="utf-8") as handle:
            if env_file.exists() and env_file.stat().st_size > 0:
                handle.write("\n")
            handle.write(f"SECRET_KEY={generated}\n")
        return generated
    except OSError:
        # 3) Último recurso: clave derivada y estable (solo desarrollo).
        import hashlib

        return hashlib.sha256(f"constru-trans-dev-{BASE_DIR}".encode()).hexdigest()


SECRET_KEY = get_secret_key()

DEFAULT_LOCAL_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
DEFAULT_CSRF_ORIGINS = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "https://localhost",
    "https://localhost:8000",
    "https://127.0.0.1",
    "https://127.0.0.1:8000",
]


def as_list(value):
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return list(value)


DEBUG = env("DEBUG", default=True)
ALLOWED_HOSTS = as_list(env("ALLOWED_HOSTS", default=DEFAULT_LOCAL_HOSTS))
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = DEFAULT_LOCAL_HOSTS
CSRF_TRUSTED_ORIGINS = as_list(env("CSRF_TRUSTED_ORIGINS", default=DEFAULT_CSRF_ORIGINS))
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = DEFAULT_CSRF_ORIGINS

# ============================================================
# APLICACIONES
# ============================================================

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = []

LOCAL_APPS = [
<<<<<<< HEAD:core/settings/base.py
    "core.apps.CoreConfig",
    "usuarios",
    "clientes",
    "catalogo",
    "compras",
    "pedidos",
    "logistica",
    "licensing",
    "ia",
    "ayuda",
=======
    "config.apps.CoreConfig","apps.usuarios","apps.clientes","apps.catalogo","apps.compras","apps.pedidos","apps.pagos","apps.reportes","apps.inicio","apps.auditoria","apps.logistica","apps.licensing","apps.ia","apps.ayuda",
>>>>>>> origin/GRUPO_7_ADSO/FIX:config/settings/base.py
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.http.ConditionalGetMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Seguridad propia: bloqueo de IP y warnings tras auth (para saber user)
    "config.middleware.SecurityMiddleware",
    # Seguridad propia: validación a nivel de URL namespace / url_name ANTES de la vista
    "config.middleware.RoleNamespaceMiddleware",
    "config.middleware.DatabasePreferenceMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Licencia: último paso antes de servir la app
    "apps.licensing.middleware.LicenseEnforcementMiddleware",
]

# ============================================================
# SEGURIDAD — Control de acceso + Bloqueo IP
# ============================================================

SECURITY_MAX_WARNINGS = 5          # Intentos no autorizados antes de bloquear
SECURITY_BLOCK_HOURS = 24          # Duración bloqueo IP (horas)
SECURITY_WARNING_WINDOW = 60       # Ventana de gracia para contar warnings (minutos)

ROOT_URLCONF = "config.urls"

# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.usuarios.context_processors.notificaciones_context",
                "apps.usuarios.context_processors.modo_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ============================================================
# BASE DE DATOS — PostgreSQL (Neon) configurada como default
# ============================================================

LOCAL_DATABASE = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
    "OPTIONS": {
        "timeout": 30,
        "check_same_thread": False,
    },
}

database_url = env("DATABASE_URL", default="")
remote_database = None
if database_url:
    remote_database = dj_database_url.parse(
        database_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
    if "OPTIONS" not in remote_database:
        remote_database["OPTIONS"] = {}
    if remote_database.get("ENGINE") == "django.db.backends.postgresql":
        remote_database["OPTIONS"].setdefault("connect_timeout", 5)
    remote_database["OPTIONS"].pop("options", None)

# Si existe la URL de base de datos remota, se asigna como 'default'
DATABASES = {
    "default": remote_database if remote_database else LOCAL_DATABASE,
    "local": LOCAL_DATABASE,
}

if remote_database:
    DATABASES["remota"] = remote_database

DATABASE_ROUTERS = ["config.routers.EnrutadorInventario"]

# ============================================================
# CACHÉ — Para precargar datos de paneles y optimizar velocidad
# ============================================================

# Crear directorio de caché si no existe
(BASE_DIR / "cache").mkdir(exist_ok=True)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": BASE_DIR / "cache",
        "TIMEOUT": 600,  # 10 minutos de caché por defecto (aumentado de 5)
        "OPTIONS": {
            "MAX_ENTRIES": 5000,  # Aumentado de 1000
        },
        "KEY_PREFIX": "constru_trans",  # Prefijo para evitar conflictos
    }
}

# ============================================================
# AUTH Y CONTRASEÑAS
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTHENTICATION_BACKENDS = [
    "apps.usuarios.backends.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ============================================================
# SESIONES Y COOKIES
# ============================================================

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = env("SESSION_COOKIE_AGE")
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False
CSRF_COOKIE_SAMESITE = "Lax"

LOGIN_URL = "/usuarios/login/"
LOGIN_REDIRECT_URL = "/usuarios/panel/"
LOGOUT_REDIRECT_URL = "/usuarios/login/"

# ============================================================
# RECUPERACIÓN DE CONTRASEÑA
# ============================================================

PASSWORD_RESET_TIMEOUT = env("PASSWORD_RESET_TIMEOUT")

# ============================================================
# EMAIL — Gmail SMTP (cuenta constru_trans)
# ============================================================

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_USE_TLS = env("EMAIL_USE_TLS")
EMAIL_USE_SSL = env("EMAIL_USE_SSL")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=f"Constru-Trans <{EMAIL_HOST_USER}>")
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
EMAIL_TIMEOUT = env("EMAIL_TIMEOUT")
RESEND_API_KEY = env("RESEND_API_KEY", default="")
RESEND_FROM_EMAIL = env("RESEND_FROM_EMAIL", default="")
OPENWEATHER_API_KEY = env("OPENWEATHER_API_KEY")

# ============================================================
# INTERNACIONALIZACIÓN
# ============================================================

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = "."
DECIMAL_SEPARATOR = ","
NUMBER_GROUPING = 3

# ============================================================
# ARCHIVOS ESTÁTICOS Y MEDIA
# ============================================================

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ============================================================
# ALMACENAMIENTO EN LA NUBE (opcional)
# ============================================================

USE_S3 = env("USE_S3")
if USE_S3:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
else:
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================
# LOGGING
# ============================================================

(BASE_DIR / "logs").mkdir(exist_ok=True)
(BASE_DIR / "media").mkdir(exist_ok=True)
(STATIC_ROOT).mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# Custom User Model
AUTH_USER_MODEL = "usuarios.Usuario"
APPEND_SLASH = False

# ============================================================
# LICENCIAMIENTO
# ============================================================

LICENSE_REQUIRED = env("LICENSE_REQUIRED")
LICENSE_SERVER_URL = env("LICENSE_SERVER_URL")
LICENSE_PUBLIC_KEY = env("LICENSE_PUBLIC_KEY")
LICENSE_HEARTBEAT_MINUTES = env("LICENSE_HEARTBEAT_MINUTES")
LICENSE_MAX_AGE_DAYS = env("LICENSE_MAX_AGE_DAYS")
<<<<<<< HEAD:core/settings/base.py
=======


>>>>>>> origin/GRUPO_7_ADSO/FIX:config/settings/base.py
