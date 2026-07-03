from django.test import Client, TestCase
from django.urls import reverse


class SmokeViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_ruta_carga(self):
        response = self.client.get(reverse("inicio:inicio"))
        self.assertEqual(response.status_code, 200)
