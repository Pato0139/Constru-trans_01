#!/usr/bin/env python
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.development")

import django  # noqa: E402
from django.conf import settings  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.contrib.auth.tokens import default_token_generator  # noqa: E402
from django.core.mail import send_mail  # noqa: E402
from django.template.loader import render_to_string  # noqa: E402
from django.utils.encoding import force_bytes  # noqa: E402
from django.utils.html import strip_tags  # noqa: E402
from django.utils.http import urlsafe_base64_encode  # noqa: E402

print("=== Probando Password Reset ===")

# Verificar usuarios
print(f"\nUsuarios en la BD: {User.objects.count()}")
for user in User.objects.all():
    print(
        f"  - ID: {user.id}, Email: {user.email}, Username: {user.username}, Active: {user.is_active}"
    )

# Elegir un email para probar
test_email = input(
    "\nIngresa un email para probar el password reset (o deja vacío para usar el primero): "
).strip()

if not test_email:
    first_user = User.objects.first()
    if first_user:
        test_email = first_user.email
        print(f"Usando: {test_email}")
    else:
        print("ERROR: No hay usuarios en la BD!")
        exit(1)

# Buscar el usuario
try:
    user = User.objects.get(email=test_email)
    print(f"\n✅ Usuario encontrado: {user.username} ({user.email})")
except User.DoesNotExist:
    print(f"\n❌ ERROR: No hay usuario con email {test_email}")
    exit(1)

# Generar token y uid
uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
token = default_token_generator.make_token(user)
print(f"\nUID: {uidb64}")
print(f"Token: {token}")

# Preparar email
context = {
    "user": user,
    "uid": uidb64,
    "token": token,
    "protocol": "http",
    "domain": "localhost:8000",
}

# Renderizar templates (usar los del proyecto)
try:
    html_message = render_to_string("registration/password_reset_email.html", context)
    plain_message = strip_tags(html_message)
    subject = render_to_string("registration/password_reset_subject.txt", context).strip()
except Exception as e:
    print(f"\n❌ Error al renderizar templates: {e}")
    print("Usando email simple...")
    plain_message = f"Hola {user.username},\n\nPara restablecer tu contraseña, visita:\nhttp://localhost:8000/reset/{uidb64}/{token}/\n\nSaludos,\nConstru-Trans"
    html_message = plain_message
    subject = "Restablecer tu contraseña en Constru-Trans"

print(f"\nEnviando email a {test_email}...")
print(f"Subject: {subject}")

try:
    result = send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [test_email],
        html_message=html_message,
        fail_silently=False,
    )
    print(f"\n✅ Email de password reset enviado exitosamente! Resultado: {result}")
    print("\nRevisa tu bandeja de entrada (y spam)!")
except Exception as e:
    print(f"\n❌ Error al enviar email: {type(e).__name__}: {e}")
    import traceback

    print("\nDetalles del error:")
    traceback.print_exc()
