from django.test import TestCase

from ordenes.models import Pedido
from pagos.models import Pago
from usuarios.models import Usuario


class PagoTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="pago-cliente",
            email="pago-cliente@test.com",
            password="password123",
            nombres="Cliente",
            apellidos="Pago",
            documento="987654321",
            tipo_documento="CC",
            rol="cliente",
        )
        self.pedido = Pedido.objects.create(
            usuario=self.usuario,
            direccion_destino="Bogotá",
            total=150000,
        )

    def test_pago_se_crea_pendiente(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            monto=150000,
            metodo="transferencia",
            referencia="TRX-001",
        )
        self.assertEqual(pago.estado, "pendiente")
        self.assertEqual(str(pago), f"Pago #{pago.pk} - Pedido #{self.pedido.pk}")
