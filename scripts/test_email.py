import os
import sys
import django

# Añadir el directorio raíz al path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email():
    print("Iniciando prueba de envío de correo...")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    
    try:
        subject = 'Prueba de Correo Constru-Trans'
        message = 'Si recibes este correo, la configuración de Brevo está funcionando correctamente.'
        email_from = settings.DEFAULT_FROM_EMAIL
        recipient_list = [settings.EMAIL_HOST_USER] # Enviarse a sí mismo para probar
        
        send_mail(subject, message, email_from, recipient_list, fail_silently=False)
        print("\n✅ ¡ÉXITO! El correo fue enviado.")
        print(f"Revisa la bandeja de entrada de: {recipient_list[0]}")
    except Exception as e:
        print("\n❌ ¡ERROR! No se pudo enviar el correo.")
        print(f"Detalle del error: {str(e)}")

if __name__ == "__main__":
    test_email()
