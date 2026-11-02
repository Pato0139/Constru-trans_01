from django.test import TestCase

from apps.clientes.models import Cliente
from apps.usuarios.models import Usuario


class ClienteModelTests(TestCase):
    """Tests para el modelo Cliente."""

    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="cliente_model",
            email="cliente.model@example.com",
            password="testpass123",
            nombres="Ana",
            apellidos="Gomez",
            documento="12345678",
            tipo_documento="CC",
            rol="cliente",
        )

    def test_ensure_for_user_crea_perfil(self):
        Cliente.objects.filter(usuario=self.user).delete()
        cliente, created = Cliente.ensure_for_user(self.user)
        self.assertTrue(created)
        self.assertEqual(cliente.usuario_id, self.user.pk)
        self.assertEqual(cliente.direccion, "Por definir")

    def test_ensure_for_user_no_duplica(self):
        Cliente.ensure_for_user(self.user)
        cliente2, created2 = Cliente.ensure_for_user(self.user)
        self.assertFalse(created2)
        self.assertEqual(
            Cliente.objects.filter(usuario=self.user).count(), 1
        )

    def test_save_sincroniza_direccion_principal(self):
        cliente = Cliente.objects.get(usuario=self.user)
        cliente.direccion = "Calle 100 # 20-30"
        cliente.save()
        cliente.refresh_from_db()
        self.assertEqual(cliente.direccion_principal, "Calle 100 # 20-30")

    def test_str_retorna_nombres(self):
        cliente = Cliente.objects.get(usuario=self.user)
        self.assertEqual(str(cliente), "Ana")

    def test_gasto_acumulado_default_cero(self):
        cliente = Cliente.objects.get(usuario=self.user)
        self.assertEqual(cliente.gasto_acumulado, 0)

    def test_tipo_cliente_default_persona(self):
        cliente = Cliente.objects.get(usuario=self.user)
        self.assertEqual(cliente.tipo_cliente, "persona")

    def test_es_vip_default_false(self):
        cliente = Cliente.objects.get(usuario=self.user)
        self.assertFalse(cliente.es_vip)

    def test_ensure_for_user_rechaza_user_none(self):
        with self.assertRaises(ValueError):
            Cliente.ensure_for_user(None)

    def test_ensure_for_user_rechaza_user_sin_pk(self):
        user_sin_pk = Usuario(
            username="sin_pk",
            email="sin.pk@example.com",
            nombres="Sin",
            apellidos="PK",
        )
        with self.assertRaises(ValueError):
            Cliente.ensure_for_user(user_sin_pk)

    def test_signal_auto_crea_perfil_cliente(self):
        nuevo = Usuario.objects.create_user(
            username="nuevo_cliente",
            email="nuevo@example.com",
            password="test123",
            nombres="Nuevo",
            apellidos="Cliente",
            documento="87654321",
            rol="cliente",
        )
        self.assertTrue(Cliente.objects.filter(usuario=nuevo).exists())

    def test_signal_no_crea_perfil_para_no_cliente(self):
        nuevo = Usuario.objects.create_user(
            username="admin_no_cliente",
            email="admin.nocliente@example.com",
            password="test123",
            nombres="Admin",
            apellidos="NoCliente",
            documento="11111111",
            rol="admin",
        )
        self.assertFalse(Cliente.objects.filter(usuario=nuevo).exists())
