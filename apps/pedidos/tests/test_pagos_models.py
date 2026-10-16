from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.usuarios.models import Usuario


class PagoModelTests(TestCase):
    def setUp(self):
        self.cliente = Usuario.objects.create_user(
            username="clientepago",
            email="clientepago@test.com",
            password="TestPassword-123!",
            nombres="Cliente",
            apellidos="Pago",
            documento="1098765432",
            tipo_documento="CC",
            rol="cliente",
        )
        self.pedido = Pedido.objects.create(
            usuario=self.cliente,
            direccion_destino="Tunja",
            estado=Pedido.PENDIENTE,
            total=Decimal("150000.00"),
        )

    def test_pago_se_crea_pendiente(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=Decimal("150000.00"),
        )

        self.assertEqual(pago.estado, Pago.PENDIENTE)
        self.assertEqual(str(pago), f"Pago pedido {self.pedido.pk} (Pendiente)")

    def test_contraentrega_no_exige_comprobante(self):
        pago = Pago(
            pedido=self.pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=Decimal("150000.00"),
        )

        pago.full_clean()
        pago.save()

        self.assertEqual(pago.estado, Pago.PENDIENTE)
        self.assertFalse(pago.habilita_despacho())

    def test_transferencia_exige_comprobante(self):
        pago = Pago(
            pedido=self.pedido,
            metodo=Pago.METODO_NEQUI,
            monto=Decimal("150000.00"),
        )

        with self.assertRaises(ValidationError):
            pago.full_clean()

    def test_model_usa_esquema_legacy_de_base_de_datos(self):
        self.assertEqual(Pago._meta.db_table, "pago_pedido")
        self.assertEqual(Pago._meta.get_field("pedido").db_column, "pedido_id")
        self.assertEqual(Pago._meta.get_field("metodo").db_column, "codigo_metodo_pago")
        self.assertEqual(Pago._meta.get_field("estado").db_column, "estado_pago")
        self.assertEqual(Pago._meta.get_field("fecha_registro").db_column, "fecha_creacion")
