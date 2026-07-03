from django.test import Client, TestCase
from django.urls import reverse

from usuarios.models import Usuario


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
