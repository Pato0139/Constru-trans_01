import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Funciones auxiliares
def env_bool(key: str, default=False) -> bool:
    val = os.getenv(key, str(default))
    return val.strip().lower() in ("1", "true", "yes", "on")

def env_list(key: str, default=""):
    val = os.getenv(key, default)
    return [x.strip() for x in val.split(",") if x.strip()]

# SEGURIDAD BÁSICA
SECRET_KEY = os.getenv("SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS", 
    "http://127.0.0.1:8000,http://localhost:8000"
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_browser_reload',

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
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # Comprimir respuestas para mayor velocidad
    'django.middleware.http.ConditionalGetMiddleware',  # Manejo de ETags para cache del navegador
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    MIDDLEWARE += ['django_browser_reload.middleware.BrowserReloadMiddleware']

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
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
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Configuración de PostgreSQL para Sincronización (Neon Cloud)
if os.getenv('DB_ENGINE') == 'django.db.backends.postgresql':
    DATABASES['remota'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'neondb'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 0,  # Importante para Serverless/Neon: cerrar conexiones rápido
        'OPTIONS': {
            'sslmode': os.getenv('DB_SSLMODE', 'require'),
            'connect_timeout': 3,  # Reducimos a 3 segundos para que el fallback sea más rápido
        }
    }

# Enrutador de base de datos para sincronización offline-first
DATABASE_ROUTERS = ['core.routers.EnrutadorInventario']

# Configuración de Sesiones y Cookies para multidispositivo (Nube)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Sesiones en la nube para compartir entre PCs
SESSION_COOKIE_AGE = 1209600  # 2 semanas en segundos
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Mantener sesión al cerrar navegador
SESSION_SAVE_EVERY_REQUEST = True  # Renovar sesión en cada interacción

# Seguridad de Cookies (Ajustar según entorno)
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
CSRF_USE_SESSIONS = True  # Almacenar CSRF en la sesión para mayor compatibilidad
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = '.'
DECIMAL_SEPARATOR = ','
NUMBER_GROUPING = 3

# STATIC FILES
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
# STATIC_ROOT = BASE_DIR / 'staticfiles' # Descomenta esto para producción (collectstatic)

# MEDIA FILES
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email (Opcional, configurado por .env)
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend') # Console para pruebas
if EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'Constru-trans <{EMAIL_HOST_USER}>')

LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/usuarios/panel/'
LOGOUT_REDIRECT_URL = '/usuarios/login/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'