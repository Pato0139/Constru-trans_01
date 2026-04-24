from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def env_bool(key: str, default=False) -> bool:
    val = os.getenv(key, str(default))
    return val.strip().lower() in ("1", "true", "yes", "on")

def env_list(key: str, default=""):
    val = os.getenv(key, default)
    return [x.strip() for x in val.split(",") if x.strip()]

#seguridad basica 
SECRET_KEY = os.getenv("SECRET_KEY", "insecure-dev-key") 
DEBUG = env_bool("DEBUG", True) 

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost") 
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS", 
    "http://127.0.0.1,http://localhost"
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Apps
    'apps.usuarios',
    'apps.clientes',
    'apps.inventario',
    'apps.compras',
    'apps.transporte',
    'apps.ordenes',
    'apps.facturacion',
    'apps.pagos',
    'apps.reportes',
    'apps.inicio',
    'apps.historial',
    'django_browser_reload',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.usuarios.context_processors.notificaciones_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = { 
    # 1. Base de datos LOCAL (Por defecto - SQLite para portabilidad)
    "default": { 
        "ENGINE": "django.db.backends.sqlite3", 
        "NAME": BASE_DIR / "db.sqlite3", 
    },
    # 2. Base de datos REMOTA (Neon.tech en la nube)
    "remota": { 
        "ENGINE": "django.db.backends.postgresql", 
        "NAME": os.getenv("DB_NAME", "neondb"), 
        "USER": os.getenv("DB_USER", "neondb_owner"), 
        "PASSWORD": os.getenv("DB_PASSWORD"), 
        "HOST": os.getenv("DB_HOST", "ep-fragrant-dew-anpj34eu.c-6.us-east-1.aws.neon.tech"), 
        "PORT": os.getenv("DB_PORT", "5432"), 
        "OPTIONS": { 
            "sslmode": os.getenv("DB_SSLMODE", "require"), 
        }, 
    } 
} 

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es-co'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_TZ = True

# Formato de números para Colombia (separador de miles con punto)
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = '.'
DECIMAL_SEPARATOR = ','
NUMBER_GROUPING = 3

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Email configuration
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend") 
EMAIL_HOST = os.getenv("EMAIL_HOST", "") 
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587")) 
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True) 
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "") 
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "") 
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER) 

# Opcional (tiempo máximo del token en segundos; ej. 1 hora) 
# PASSWORD_RESET_TIMEOUT = 3600 

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Seguridad para Producción
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000 # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/usuarios/panel/'
LOGOUT_REDIRECT_URL = '/usuarios/login/'

DATABASE_ROUTERS = ['core.routers.EnrutadorInventario']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
