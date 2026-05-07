from twilio.rest import Client
from django.conf import settings
import re


def limpiar_telefono(telefono):
    if not telefono:
        return telefono
    return re.sub(r'[^0-9]', '', telefono)


def formatear_e164(telefono, codigo_pais='57'):
    telefono_limpio = limpiar_telefono(telefono)
    if not telefono_limpio:
        return telefono_limpio
    
    if telefono_limpio.startswith('+'):
        return telefono_limpio
    
    if telefono_limpio.startswith(codigo_pais) and len(telefono_limpio) > len(codigo_pais):
        return '+' + telefono_limpio
    
    if len(telefono_limpio) == 10 and telefono_limpio.startswith('3'):
        return '+' + codigo_pais + telefono_limpio
    
    return '+' + codigo_pais + telefono_limpio


class TwilioService:
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    def enviar_sms(self, telefono, mensaje):
        telefono_formateado = formatear_e164(telefono)
        return self.client.messages.create(
            body=mensaje,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=telefono_formateado
        )

    def enviar_whatsapp(self, telefono, mensaje):
        telefono_formateado = formatear_e164(telefono)
        return self.client.messages.create(
            body=mensaje,
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=f'whatsapp:{telefono_formateado}'
        )
