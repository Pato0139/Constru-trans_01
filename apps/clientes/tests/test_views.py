from django.test import Client, TestCase
from django.urls import reverse

from apps.usuarios.models import Usuario
from config.despacho import construir_direccion_destino, separar_direccion_destino


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
            rol="cliente",
        )

    def test_ruta_carga(self):
        self.client.login(username="adminsmoke", password="password123")
        response = self.client.get(reverse("clientes:mis_pedidos"))
        self.assertEqual(response.status_code, 200)

    def test_direccion_destino_usa_formato_ciudad_y_detalle(self):
        direccion = construir_direccion_destino("Bogotá", "Calle 123 # 45-67")
        self.assertEqual(direccion, "Bogotá Calle 123 # 45-67")
        self.assertEqual(separar_direccion_destino(direccion), ("Bogotá", "Calle 123 # 45-67"))
