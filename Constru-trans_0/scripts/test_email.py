
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')

print("Configuración:")
print(f"EMAIL_HOST: {EMAIL_HOST}")
print(f"EMAIL_PORT: {EMAIL_PORT}")
print(f"EMAIL_HOST_USER: {EMAIL_HOST_USER}")
print(f"Longitud de contraseña: {len(EMAIL_HOST_PASSWORD) if EMAIL_HOST_PASSWORD else 0} caracteres")
print()

try:
    print("Intentando conectar...")
    server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
    server.ehlo()
    print("EHLO OK")
    server.starttls()
    print("STARTTLS OK")
    server.ehlo()
    print("EHLO después de TLS OK")
    
    print(f"Intentando login con usuario: {EMAIL_HOST_USER}")
    server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    print("LOGIN OK!")
    
    print("Enviando correo de prueba...")
    msg = MIMEText("Este es un correo de prueba desde Django!")
    msg['Subject'] = "Prueba de correo"
    msg['From'] = DEFAULT_FROM_EMAIL
    msg['To'] = EMAIL_HOST_USER
    
    server.sendmail(msg['From'], [msg['To']], msg.as_string())
    print("CORREO ENVIADO!")
    
    server.quit()
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

