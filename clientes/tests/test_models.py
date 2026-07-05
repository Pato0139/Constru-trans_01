from django.test import TestCase

from clientes.models import Cliente
from usuarios.models import Usuario


class ClienteProfileTests(TestCase):
    def test_ensure_for_user_creates_profile_for_saved_user(self):
        user = Usuario.objects.create_user(
            username="cliente_test",
            email="cliente.test@example.com",
            password="secret123",
            nombres="Cliente",
            apellidos="Prueba",
            documento="12345678",
            tipo_documento="CC",
            rol="cliente",
        )

        Cliente.objects.filter(usuario=user).delete()

        cliente, created = Cliente.ensure_for_user(user)

        self.assertTrue(created)
        self.assertEqual(cliente.usuario_id, user.id)
        self.assertTrue(Cliente.objects.filter(usuario=user).exists())

    def test_ensure_for_user_rejects_missing_user(self):
        user = Usuario.objects.create_user(
            username="cliente_eliminado",
            email="cliente.eliminado@example.com",
            password="secret123",
            nombres="Cliente",
            apellidos="Eliminado",
            documento="87654321",
            tipo_documento="CC",
            rol="cliente",
        )
        user.delete()

        with self.assertRaises(ValueError):
            Cliente.ensure_for_user(user)
