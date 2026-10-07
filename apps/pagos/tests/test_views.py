from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.pedidos.models import Pedido
from apps.usuarios.models import Usuario

from apps.pagos.models import Pago


class PagoViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cliente = Usuario.objects.create_user(
            username="clientepagoview",
            email="clientepagoview@test.com",
            password="password123",
            nombres="Cliente",
            apellidos="Vista",
            documento="1098000001",
            tipo_documento="CC",
            rol="cliente",
        )
        self.otro = Usuario.objects.create_user(
            username="otropago",
            email="otropago@test.com",
            password="password123",
            nombres="Otro",
            apellidos="Cliente",
            documento="1098000002",
            tipo_documento="CC",
            rol="cliente",
        )
        self.admin = Usuario.objects.create_user(
            username="adminpago",
            email="adminpago@test.com",
            password="password123",
            nombres="Admin",
            apellidos="Pago",
            documento="1098000003",
            tipo_documento="CC",
            rol="admin",
        )
        self.pedido = Pedido.objects.create(
            usuario=self.cliente,
            direccion_destino="Tunja",
            estado=Pedido.PENDIENTE,
            total=120000,
        )

    def test_cliente_registra_pago_pendiente(self):
        self.client.login(username="clientepagoview", password="password123")
        comprobante = SimpleUploadedFile("recibo.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response = self.client.post(
            reverse("pagos:registrar_pago", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_NEQUI, "monto": "120000", "comprobante": comprobante},
        )
        self.assertEqual(response.status_code, 302)
        pago = Pago.objects.get(pedido=self.pedido)
        self.assertEqual(pago.estado, Pago.PENDIENTE)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.PENDIENTE)

    def test_aprobar_pago_autoriza_despacho(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=120000,
            estado=Pago.PENDIENTE,
        )
        self.client.login(username="adminpago", password="password123")
        response = self.client.post(
            reverse("pagos:revisar_pago", args=[pago.pk]),
            {"accion": "aprobar", "observaciones": "Validado"},
        )
        self.assertEqual(response.status_code, 302)
        pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(pago.estado, Pago.APROBADO)
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

    def test_rechazar_pago_no_autoriza_despacho(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=120000,
            estado=Pago.PENDIENTE,
        )
        self.client.login(username="adminpago", password="password123")
        response = self.client.post(
            reverse("pagos:revisar_pago", args=[pago.pk]),
            {"accion": "rechazar", "observaciones": "Comprobante ilegible"},
        )
        self.assertEqual(response.status_code, 302)
        pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(pago.estado, Pago.RECHAZADO)
        self.assertEqual(self.pedido.estado, Pedido.PENDIENTE)

    def test_cliente_no_ve_pago_ajeno(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=120000,
        )
        self.client.login(username="otropago", password="password123")
        response = self.client.get(reverse("pagos:detalle_pago", args=[pago.pk]))
        self.assertEqual(response.status_code, 302)
