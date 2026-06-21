#!/usr/bin/env python
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.development")

import django  # noqa: E402
from django.conf import settings  # noqa: E402

django.setup()

from django.core.mail import send_mail  # noqa: E402

print("=== Probando envío de email... ===")
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print()

try:
    result = send_mail(
        "Prueba de email Constru-Trans",
        "¡Funciona! Si recibes este email, la configuración es correcta.",
        settings.DEFAULT_FROM_EMAIL,
        [settings.EMAIL_HOST_USER],
        fail_silently=False,
    )
    print(f"✅ Email enviado exitosamente! Resultado: {result}")
except Exception as e:
    print(f"❌ Error al enviar email: {type(e).__name__}: {e}")
    import traceback

    print("\nDetalles del error:")
    traceback.print_exc()
