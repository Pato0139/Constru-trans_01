from django.test import Client, TestCase
from django.urls import reverse

from apps.auditoria.models import Historial
from apps.usuarios.models import Usuario


class SmokeViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username="adminsmoke",
            email="adminsmoke@test.com",
            password="password123",
            nombres="Admin",
            apellidos="Smoke",
            documento="555444333",
            tipo_documento="CC",
            rol="admin",
        )
        Historial.objects.create(
            usuario=self.admin,
            accion="login",
            modulo="usuarios",
            descripcion="Inicio de sesión de prueba",
            ip_address="192.168.32.1",
        )

    def test_ruta_carga(self):
        self.client.login(username="adminsmoke", password="password123")
        response = self.client.get(reverse("auditoria:lista_historial"))
        self.assertEqual(response.status_code, 200)

    def test_json_ip_formato_de_seguido_sin_descuadre(self):
        self.client.login(username="adminsmoke", password="password123")
        response = self.client.get(
            reverse("auditoria:lista_historial"),
            {"format": "json", "draw": 1, "start": 0, "length": 10},
        )
        self.assertEqual(response.status_code, 200)
        datos = response.json()
        self.assertIn("data", datos)
        self.assertTrue(len(datos["data"]) > 0)
        fila = datos["data"][0]
        # Columna 8 es la IP
        ip_html = fila[8]
        self.assertIn("192.168.32.1", ip_html)
        self.assertIn("text-nowrap", ip_html)
        self.assertIn("font-monospace", ip_html)
