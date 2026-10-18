from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.catalogo.models import MaterialConstruccion, UnidadMedida
from apps.pagos.models import Factura
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

    def test_cliente_puede_ver_sus_facturas(self):
        factura = Factura.objects.create(
            pedido=self.pedido,
            cliente=self.cliente.perfil_cliente,
            subtotal=120000,
            total=120000,
        )
        self.client.force_login(self.cliente)

        response = self.client.get(reverse("pagos:mis_facturas"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, factura.numero)

    def test_registro_pago_contraentrega_asigna_fechas_correctas(self):
        self.client.force_login(self.cliente)
        response = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_CONTRAENTREGA},
        )
        self.assertEqual(response.status_code, 302)
        pago = Pago.objects.get(pedido=self.pedido)
        self.assertEqual(pago.estado, Pago.PENDIENTE)
        self.assertEqual(pago.metodo, Pago.METODO_CONTRAENTREGA)
        self.assertIsNotNone(pago.fecha_registro)
        self.assertIsNone(pago.fecha_revision)
        self.assertIsNone(pago.revisado_por)
        self.assertFalse(bool(pago.comprobante))

    def test_registro_pago_daviplata_con_jpg(self):
        self.client.force_login(self.cliente)
        comprobante = SimpleUploadedFile(
            "comprobante.jpg",
            b"\xff\xd8\xff\xe0" + b"\x00" * 32,
            content_type="image/jpeg",
        )
        response = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_DAVIPLATA, "comprobante": comprobante},
        )
        self.assertEqual(response.status_code, 302)
        pago = Pago.objects.get(pedido=self.pedido)
        self.assertEqual(pago.estado, Pago.PENDIENTE)
        self.assertEqual(pago.metodo, Pago.METODO_DAVIPLATA)
        self.assertIsNotNone(pago.fecha_registro)
        self.assertIsNone(pago.fecha_revision)

    def test_registro_pago_bancolombia_con_png(self):
        self.client.force_login(self.cliente)
        comprobante = SimpleUploadedFile(
            "recibo_banco.png",
            b"\x89PNG\r\n\x1a\n" + b"\x00" * 32,
            content_type="image/png",
        )
        response = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_BANCOLOMBIA, "comprobante": comprobante},
        )
        self.assertEqual(response.status_code, 302)
        pago = Pago.objects.get(pedido=self.pedido)
        self.assertEqual(pago.estado, Pago.PENDIENTE)
        self.assertEqual(pago.metodo, Pago.METODO_BANCOLOMBIA)
        self.assertIsNotNone(pago.fecha_registro)
        self.assertIsNone(pago.fecha_revision)

    def test_metodos_con_comprobante_exigen_archivo(self):
        self.client.force_login(self.cliente)
        for metodo in (Pago.METODO_NEQUI, Pago.METODO_DAVIPLATA, Pago.METODO_BANCOLOMBIA):
            response = self.client.post(
                reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
                {"metodo": metodo},
            )
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Pago.objects.filter(pedido=self.pedido).exists())
            self.assertIn(
                "Este método de pago requiere comprobante.",
                response.context["form"].errors.get("comprobante", []),
            )

    def test_rechazo_comprobante_invalido_bytes_falsos(self):
        self.client.force_login(self.cliente)
        archivo_falso = SimpleUploadedFile(
            "comprobante.png",
            b"ESTO NO ES UN ARCHIVO PNG REAL",
            content_type="image/png",
        )
        response = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_NEQUI, "comprobante": archivo_falso},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Pago.objects.filter(pedido=self.pedido).exists())

    def test_reenvio_pago_despues_de_rechazo_resetea_fecha_revision(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=120000,
            estado=Pago.PENDIENTE,
        )
        # Admin rechaza
        self.client.force_login(self.admin)
        self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[pago.pk]),
            {"accion": "rechazar", "observaciones": "Dirección incompleta"},
        )
        pago.refresh_from_db()
        self.assertEqual(pago.estado, Pago.RECHAZADO)
        self.assertIsNotNone(pago.fecha_revision)
        self.assertEqual(pago.revisado_por, self.admin)

        # Cliente reenvía pago corregido
        self.client.force_login(self.cliente)
        response = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_CONTRAENTREGA},
        )
        self.assertEqual(response.status_code, 302)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, Pago.PENDIENTE)
        self.assertIsNone(pago.fecha_revision)
        self.assertIsNone(pago.revisado_por)
        self.assertEqual(pago.observaciones, "")

    def test_prevencion_pagos_duplicados_mismo_pedido(self):
        self.client.force_login(self.cliente)
        # Primer envío
        res1 = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_CONTRAENTREGA},
        )
        self.assertEqual(res1.status_code, 302)
        self.assertEqual(Pago.objects.filter(pedido=self.pedido).count(), 1)
        primer_pago_id = Pago.objects.get(pedido=self.pedido).pk

        # Segundo envío repetido (ej. doble clic o retry)
        res2 = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_CONTRAENTREGA},
        )
        self.assertEqual(res2.status_code, 302)
        self.assertEqual(Pago.objects.filter(pedido=self.pedido).count(), 1)
        self.assertEqual(Pago.objects.get(pedido=self.pedido).pk, primer_pago_id)

    def test_cliente_no_puede_registrar_pago_pedido_ajeno(self):
        self.client.force_login(self.otro)
        response = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_CONTRAENTREGA},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Pago.objects.filter(pedido=self.pedido).exists())
