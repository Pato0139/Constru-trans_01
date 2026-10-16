from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.catalogo.models import MaterialConstruccion, UnidadMedida
from apps.pedidos.models import DetallePedido
from apps.pedidos.models import Pago
from apps.pedidos.models import Pedido
from apps.usuarios.models import Usuario

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
        self.unidad = UnidadMedida.objects.create(
            codigo="UND",
            nombre="Unidad",
            abreviatura="und",
        )
        self.material = MaterialConstruccion.objects.create(
            nombre="Cemento de prueba",
            unidad_medida=self.unidad,
            descripcion="Material para validar pagos",
            precio_referencia=40000,
        )

    def test_cliente_registra_pago_pendiente(self):
        self.client.login(username="clientepagoview", password="password123")
        comprobante = SimpleUploadedFile(
            "recibo.png",
            b"\x89PNG\r\n\x1a\n",
            content_type="image/png",
        )
        response = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_NEQUI, "monto": "120000", "comprobante": comprobante},
        )
        self.assertEqual(response.status_code, 302)
        pago = Pago.objects.get(pedido=self.pedido)
        self.assertEqual(pago.estado, Pago.PENDIENTE)
        self.assertEqual(pago.monto, self.pedido.total)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.PENDIENTE)

    def test_recalcula_pedido_desde_detalles_antes_de_registrar_pago(self):
        DetallePedido.objects.create(
            pedido=self.pedido,
            material=self.material,
            cantidad=3,
            precio_unitario=self.material.precio_referencia,
        )
        self.pedido.total = 0
        self.pedido.precio = 0
        self.pedido.save(update_fields=["total", "precio"])
        self.client.force_login(self.cliente)

        response = self.client.get(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["pedido"].total, 120000)
        self.assertContains(response, "120.000")
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.total, 0)

    def test_no_permite_registrar_pago_si_el_pedido_no_tiene_valor(self):
        self.pedido.total = 0
        self.pedido.precio = 0
        self.pedido.save(update_fields=["total", "precio"])
        self.client.force_login(self.cliente)

        response = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_CONTRAENTREGA, "monto": "0"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Pago.objects.filter(pedido=self.pedido).exists())

    def test_aprobar_pago_autoriza_despacho(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=120000,
            estado=Pago.PENDIENTE,
        )
        self.client.login(username="adminpago", password="password123")
        response = self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[pago.pk]),
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
            reverse("pagos:revisar_pago_pedido", args=[pago.pk]),
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
        self.assertEqual(response.status_code, 403)
