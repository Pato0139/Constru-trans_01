import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django  # noqa: E402
from django.conf import settings  # noqa: E402
from django.core.mail import send_mail  # noqa: E402

django.setup()

print("Configuración de Django cargada:")
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(
    f"Longitud de EMAIL_HOST_PASSWORD: {len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 0}"
)
print()

try:
    print("Intentando enviar correo con Django...")
    result = send_mail(
        "Prueba desde Django",
        "¡Funciona!",
        settings.DEFAULT_FROM_EMAIL,
        [settings.EMAIL_HOST_USER],
        fail_silently=False,
    )
    print(f"CORREO ENVIADO! Resultado: {result}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
