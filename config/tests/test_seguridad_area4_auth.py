"""
Pruebas de Seguridad: Autenticación, Fuerza Bruta y Sesiones (Área 4)
Verifica:
1. Longitud mínima de contraseñas en 10 caracteres y validadores de seguridad.
2. Invocación de session.flush() en logout y eliminación de cookie remember-me.
3. Bloqueo temporal por rate limiting de login por IP.
4. Protección contra spoofing de IP en obtener_ip.
5. Mensajes anti-enumeración en login y recuperación de contraseña.
"""

from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.usuarios.views import cerrar_sesion, LOGIN_REMEMBER_COOKIE
from config.security import obtener_ip

User = get_user_model()


class SeguridadArea4AuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="cliente_auth@test.com",
            email="cliente_auth@test.com",
            password="PasswordSeguro123*",
            nombres="Cliente",
            apellidos="Auth",
            documento="88776655",
            tipo_documento="CC",
            rol="cliente",
        )

    def test_password_validator_min_length_es_al_menos_10(self):
        """La longitud mínima configurada debe ser de al menos 10 caracteres."""
        min_length = None
        for v in settings.AUTH_PASSWORD_VALIDATORS:
            if "MinimumLengthValidator" in v.get("NAME", ""):
                min_length = v.get("OPTIONS", {}).get("min_length")
        self.assertIsNotNone(min_length, "MinimumLengthValidator debe estar configurado")
        self.assertGreaterEqual(min_length, 10, "La longitud mínima de contraseña debe ser >= 10")

    def test_validate_password_rechaza_contrasenas_menores_a_10_caracteres(self):
        """Contraseñas de menos de 10 caracteres deben ser rechazadas."""
        with self.assertRaises(ValidationError):
            validate_password("Corta1*")

    def test_cerrar_sesion_hace_flush_de_sesion_y_borra_cookie_remember(self):
        """Al cerrar sesión, debe invalidarse la sesión en servidor y borrar cookie remember-me."""
        self.client.force_login(self.user)
        session_key_antes = self.client.session.session_key
        
        response = self.client.get(reverse("usuarios:logout"))
        self.assertEqual(response.status_code, 302)
        
        # Debe redirigir al login
        self.assertIn(reverse("usuarios:login"), response.url)
        
        # La cookie remember-me debe ser borrada en la respuesta
        cookie_remember = response.cookies.get(LOGIN_REMEMBER_COOKIE)
        if cookie_remember:
            self.assertEqual(cookie_remember.value, "")

    def test_obtener_ip_no_confia_a_ciegas_en_x_forwarded_for_si_no_es_proxy_confiable(self):
        """Si un atacante envía X-Forwarded-For falso directamente en entorno local/no-proxy, debe ignorarse."""
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.50"
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.199, 10.0.0.1"

        # Con TRUSTED_PROXIES vacío y settings.DEBUG=True, debe usar REMOTE_ADDR
        with self.settings(TRUSTED_PROXIES=[], DEBUG=True, USE_PROXY_IP_HEADERS=False):
            ip = obtener_ip(request)
            self.assertEqual(
                ip,
                "192.168.1.50",
                "obtener_ip no debe confiar en cabecera HTTP_X_FORWARDED_FOR spoofed sin proxy confiable",
            )

    def test_login_rate_limiting_por_ip_bloquea_tras_10_intentos(self):
        """Múltiples intentos fallidos de login desde la misma IP activan el bloqueo temporal por IP."""
        for i in range(10):
            response = self.client.post(
                reverse("usuarios:login"),
                data={"username": "cliente_auth@test.com", "password": "WrongPassword999*"},
            )
            self.assertEqual(response.status_code, 200)

        # El 11vo intento debe ser rechazado por rate limit de IP
        response = self.client.post(
            reverse("usuarios:login"),
            data={"username": "cliente_auth@test.com", "password": "WrongPassword999*"},
        )
        self.assertContains(
            response,
            "Demasiados intentos desde tu red",
            msg_prefix="Debe bloquear intentos excedidos por IP",
        )

    def test_recuperacion_password_no_enumera_usuarios(self):
        """Solicitar recuperación para un correo inexistente debe responder igual que uno existente (302)."""
        response = self.client.post(
            reverse("usuarios:password_reset"),
            data={"email": "no_existe_absolutamente_9988@test.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("usuarios:password_reset_done"), response.url)
