
import os
import django
from pathlib import Path
import environ

# Set up Django
BASE_DIR = Path(__file__).resolve().parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.conf import settings

print("DEBUG (settings):", settings.DEBUG)
print("ALLOWED_HOSTS (settings):", settings.ALLOWED_HOSTS)
print("DATABASES keys:", list(settings.DATABASES.keys()))
if "remota" in settings.DATABASES:
    print("DATABASES['remota'] ENGINE:", settings.DATABASES['remota'].get('ENGINE'))
    print("DATABASES['remota'] OPTIONS:", settings.DATABASES['remota'].get('OPTIONS'))

print("\nDEBUG (env):", env("DEBUG"))
print("DATABASE_URL from env:", env("DATABASE_URL", default="not set"))
