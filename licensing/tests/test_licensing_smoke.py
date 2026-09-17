import hashlib
from pathlib import Path

from django.test import Client, TestCase
from django.urls import reverse

from licensing.services import calculate_build_hash, calculate_manifest_hash
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
            rol="admin",
        )

    def test_ruta_carga(self):
        self.client.login(username="adminsmoke", password="password123")
        response = self.client.get(reverse("licensing:license_expired"))
        self.assertEqual(response.status_code, 200)

    def test_hashes_de_integridad_no_son_vacios(self):
        build_hash = calculate_build_hash()
        manifest_hash = calculate_manifest_hash()

        self.assertNotEqual(build_hash, hashlib.sha256(b"").hexdigest())
        self.assertNotEqual(manifest_hash, hashlib.sha256(b"").hexdigest())
        self.assertEqual(len(build_hash), 64)
        self.assertEqual(len(manifest_hash), 64)
        project_root = Path(__file__).resolve().parents[2]
        self.assertTrue((project_root / "licensing" / "models.py").exists())
