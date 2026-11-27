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
            documento="5554443330",
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

    def test_json_cinco_columnas_con_fecha_y_hora_apiladas(self):
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
        # Columnas: 0=ID, 1=Usuario, 2=Módulo, 3=Fecha y Hora, 4=Acción
        self.assertEqual(len(fila), 5)
        self.assertIn("auditoria-datetime-stack", fila[3])
        self.assertIn("auditoria-time", fila[3])
        self.assertIn("auditoria-date", fila[3])
