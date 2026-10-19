from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.catalogo.models import MaterialConstruccion
from apps.clientes.models import Cliente
from apps.logistica.models import Entrega, Vehiculo
from apps.pagos.models import Pago
from apps.pedidos.models import DetallePedido, Pedido
from apps.usuarios.models import Conductor, Usuario


class PanelesClienteTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Cliente 1
        self.user1 = Usuario.objects.create_user(
            username="cliente1",
            email="cliente1@test.com",
            password="password123",
            nombres="Juan",
            apellidos="Perez",
            documento="111222333",
            tipo_documento="CC",
            telefono="3001234567",
            rol="cliente",
        )
        self.cliente1, _ = Cliente.ensure_for_user(self.user1)
        self.cliente1.direccion = "Calle 10 # 20-30"
        self.cliente1.save()

        # Cliente 2
        self.user2 = Usuario.objects.create_user(
            username="cliente2",
            email="cliente2@test.com",
            password="password123",
            nombres="Maria",
            apellidos="Gomez",
            documento="444555666",
            tipo_documento="CC",
            telefono="3009876543",
            rol="cliente",
        )
        self.cliente2, _ = Cliente.ensure_for_user(self.user2)
        self.cliente2.direccion = "Carrera 40 # 50-60"
        self.cliente2.save()

        # Conductor
        self.user_cond = Usuario.objects.create_user(
            username="conductor1",
            email="conductor1@test.com",
            password="password123",
            nombres="Carlos",
            apellidos="Rueda",
            documento="777888999",
            tipo_documento="CC",
            telefono="3110001122",
            rol="conductor",
        )
        self.conductor, _ = Conductor.ensure_for_user(self.user_cond)

        # Vehiculo
        self.vehiculo = Vehiculo.objects.create(
            placa="ABC123",
            marca="Chevrolet",
            modelo="NPR",
            tipo_vehiculo="Camión",
            capacidad_carga=Decimal("5.0"),
        )

        from apps.catalogo.models import UnidadMedida

        # Unidad
        self.unidad, _ = UnidadMedida.objects.get_or_create(
            codigo="BUL",
            defaults={"nombre": "Bulto", "abreviatura": "bulto"},
        )

        # Material
        self.material = MaterialConstruccion.objects.create(
            nombre="Cemento Gris",
            descripcion="Bulto de 50kg",
            precio_referencia=Decimal("28000.00"),
            unidad_medida=self.unidad,
        )

    def test_cliente_solo_ve_sus_propios_pedidos_activos(self):
        pedido1 = Pedido.objects.create(
            usuario=self.user1,
            cliente=self.cliente1,
            direccion_destino="Calle 10 # 20-30",
            estado=Pedido.PENDIENTE,
        )
        pedido2 = Pedido.objects.create(
            usuario=self.user2,
            cliente=self.cliente2,
            direccion_destino="Carrera 40 # 50-60",
            estado=Pedido.PENDIENTE,
        )

        self.client.force_login(self.user1)
        response = self.client.get(reverse("clientes:mis_pedidos"))
        self.assertEqual(response.status_code, 200)

        pedidos_en_vista = response.context["pedidos"]
        self.assertIn(pedido1, pedidos_en_vista)
        self.assertNotIn(pedido2, pedidos_en_vista)

    def test_pedidos_activos_vs_historial_separacion(self):
        pedido_activo = Pedido.objects.create(
            usuario=self.user1,
            cliente=self.cliente1,
            direccion_destino="Destino Activo",
            estado=Pedido.PENDIENTE,
        )
        pedido_entregado = Pedido.objects.create(
            usuario=self.user1,
            cliente=self.cliente1,
            direccion_destino="Destino Entregado",
            estado=Pedido.ENTREGADO,
        )
        pedido_cancelado = Pedido.objects.create(
            usuario=self.user1,
            cliente=self.cliente1,
            direccion_destino="Destino Cancelado",
            estado=Pedido.CANCELADO,
        )

        self.client.force_login(self.user1)

        resp_activos = self.client.get(reverse("clientes:mis_pedidos"))
        self.assertEqual(resp_activos.status_code, 200)
        pedidos_activos = resp_activos.context["pedidos"]
        self.assertIn(pedido_activo, pedidos_activos)
        self.assertNotIn(pedido_entregado, pedidos_activos)
        self.assertNotIn(pedido_cancelado, pedidos_activos)

        resp_historial = self.client.get(reverse("clientes:historial_pedidos"))
        self.assertEqual(resp_historial.status_code, 200)
        pedidos_historial = resp_historial.context["pedidos"]
        self.assertIn(pedido_entregado, pedidos_historial)
        self.assertIn(pedido_cancelado, pedidos_historial)
        self.assertNotIn(pedido_activo, pedidos_historial)

    def test_cliente_solo_ve_sus_propios_pagos(self):
        pedido1 = Pedido.objects.create(
            usuario=self.user1,
            cliente=self.cliente1,
            direccion_destino="Destino 1",
            estado=Pedido.PENDIENTE,
        )
        pago1 = Pago.objects.create(
            pedido=pedido1,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=Decimal("150000.00"),
            estado=Pago.PENDIENTE,
        )

        pedido2 = Pedido.objects.create(
            usuario=self.user2,
            cliente=self.cliente2,
            direccion_destino="Destino 2",
            estado=Pedido.PENDIENTE,
        )
        pago2 = Pago.objects.create(
            pedido=pedido2,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=Decimal("200000.00"),
            estado=Pago.PENDIENTE,
        )

        self.client.force_login(self.user1)
        resp_pagos = self.client.get(reverse("pagos:mis_pagos"))
        self.assertEqual(resp_pagos.status_code, 200)
        pagos_en_vista = resp_pagos.context["pagos"]
        self.assertIn(pago1, pagos_en_vista)
        self.assertNotIn(pago2, pagos_en_vista)

    def test_seguridad_cliente_no_puede_ver_pago_ajeno_ni_comprobante(self):
        pedido2 = Pedido.objects.create(
            usuario=self.user2,
            cliente=self.cliente2,
            direccion_destino="Destino 2",
            estado=Pedido.PENDIENTE,
        )
        fake_img = SimpleUploadedFile("comprobante.jpg", b"fakecontent", content_type="image/jpeg")
        pago2 = Pago.objects.create(
            pedido=pedido2,
            metodo=Pago.METODO_NEQUI,
            monto=Decimal("200000.00"),
            estado=Pago.PENDIENTE,
            comprobante=fake_img,
        )

        self.client.force_login(self.user1)
        resp_detalle = self.client.get(reverse("pagos:detalle_pago", args=[pago2.pk]))
        self.assertIn(resp_detalle.status_code, [403, 302])

        resp_comprobante = self.client.get(reverse("pagos:ver_comprobante_pago", args=[pago2.pk]))
        self.assertIn(resp_comprobante.status_code, [403, 302])

    def test_pago_rechazado_muestra_motivo_en_detalle(self):
        pedido1 = Pedido.objects.create(
            usuario=self.user1,
            cliente=self.cliente1,
            direccion_destino="Destino 1",
            estado=Pedido.PENDIENTE,
        )
        pago1 = Pago.objects.create(
            pedido=pedido1,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=Decimal("150000.00"),
            estado=Pago.RECHAZADO,
            observaciones="Comprobante ilegible o monto incompleto.",
        )

        self.client.force_login(self.user1)
        resp = self.client.get(reverse("pagos:detalle_pago", args=[pago1.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Comprobante ilegible o monto incompleto.")
        self.assertContains(resp, "Rechazado")
        self.assertContains(resp, reverse("pagos:registrar_pago_pedido", args=[pedido1.codigo_pedido]))

    def test_detalle_pedido_muestra_items_precios_y_logistica(self):
        pedido = Pedido.objects.create(
            usuario=self.user1,
            cliente=self.cliente1,
            direccion_origen="Bodega Central",
            direccion_destino="Avenida 68 # 80-90",
            estado=Pedido.EN_RUTA,
        )
        DetallePedido.objects.create(
            pedido=pedido,
            material=self.material,
            cantidad=10,
            precio_unitario=Decimal("28000.00"),
            subtotal=Decimal("280000.00"),
        )
        pedido.calcular_total()

        Entrega.objects.create(
            pedido=pedido,
            conductor=self.conductor,
            vehiculo=self.vehiculo,
            estado="en_ruta",
        )

        self.client.force_login(self.user1)
        resp = self.client.get(reverse("pedidos:ver_pedido_admin", args=[pedido.codigo_pedido]))
        self.assertEqual(resp.status_code, 200)

        self.assertContains(resp, "Cemento Gris")
        self.assertContains(resp, "280.000")
        self.assertContains(resp, "ABC123")
        self.assertContains(resp, "Carlos Rueda")
        self.assertContains(resp, "Progreso del Pedido")

    def test_seguimiento_pedidos_redirecciona_a_mis_pedidos(self):
        self.client.force_login(self.user1)
        resp = self.client.get(reverse("clientes:seguimiento_pedidos"))
        self.assertRedirects(resp, reverse("clientes:mis_pedidos"))

    def test_cliente_puede_cancelar_pedido_pendiente(self):
        pedido = Pedido.objects.create(
            usuario=self.user1,
            cliente=self.cliente1,
            direccion_destino="Calle 10 # 20-30",
            estado=Pedido.PENDIENTE,
        )
        DetallePedido.objects.create(
            pedido=pedido,
            material=self.material,
            cantidad=5,
            precio_unitario=Decimal("28000.00"),
            subtotal=Decimal("140000.00"),
        )
        self.client.force_login(self.user1)
        resp = self.client.post(reverse("clientes:cancelar_pedido", args=[pedido.codigo_pedido]))
        self.assertRedirects(resp, reverse("clientes:mis_pedidos"))
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.CANCELADO)

