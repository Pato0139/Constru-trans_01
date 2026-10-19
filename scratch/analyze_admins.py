import os
import sys

sys.path.insert(0, os.getcwd())
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.usuarios.models import Usuario

admins = Usuario.objects.filter(rol='admin').order_by('id')
print(f"Total cuentas rol='admin': {admins.count()}\n")

superadmin_email = os.getenv("SUPERADMIN_EMAIL", "superadmin@constru-trans.com").lower()
superadmin_user = os.getenv("SUPERADMIN_USERNAME", "superadmin").lower()

print(f"{'ID':3s} | {'Identificador':25s} | {'rol':6s} | {'is_act':6s} | {'is_sup':6s} | {'is_sta':6s} | {'Creación':19s} | {'Último Acceso':19s} | {'Coincide Superadmin'}")
print("-" * 125)

for a in admins:
    ident = a.email or a.username or "sin_ident"
    creado = str(a.date_joined)[:19] if a.date_joined else "Desconocida"
    ultimo = str(a.last_login)[:19] if a.last_login else "Nunca"
    
    is_super_match = (a.username.lower() == superadmin_user or a.email.lower() == superadmin_email)
    match_str = "SÍ (SUPERADMIN)" if is_super_match else "No"
    
    print(f"{a.id:3d} | {ident:25s} | {a.rol:6s} | {str(a.is_active):6s} | {str(a.is_superuser):6s} | {str(a.is_staff):6s} | {creado:19s} | {ultimo:19s} | {match_str}")
