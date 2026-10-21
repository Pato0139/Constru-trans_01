import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.usuarios.models import Usuario

admins = Usuario.objects.filter(rol='admin').order_by('id')
print(f"Total administradores encontrados: {admins.count()}\n")
print(f"{'ID':3s} | {'Identificador Enmascarado':30s} | {'Fecha Creación':19s} | {'Último Acceso':19s} | {'is_staff'}")
print("-" * 90)

for a in admins:
    email = a.email or a.username or "sin_email"
    if "@" in email:
        user_part, domain_part = email.split("@", 1)
        masked = f"{user_part[:2]}***@{domain_part}"
    else:
        masked = f"{email[:2]}***"
    
    creado = str(a.date_joined)[:19] if a.date_joined else "Desconocida"
    ultimo = str(a.last_login)[:19] if a.last_login else "Nunca"
    print(f"{a.id:3d} | {masked:30s} | {creado:19s} | {ultimo:19s} | {a.is_staff}")
