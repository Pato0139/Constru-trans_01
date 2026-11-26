from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.catalogo.models import Catalogo, MaterialConstruccion, Stock, UnidadMedida
from apps.clientes.models import Cliente
from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.usuarios.models import Usuario


class TarifaEnvioYMinimoPedidoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cliente_user = Usuario.objects.create_user(
            username="cliente_envio",
            email="cliente_envio@constru-trans.com",
            password="Password123!",
            nombres="Laura",
            apellidos="Gómez",
            documento="1020304050",
            tipo_documento="CC",
            rol="cliente",
        )
        Cliente.ensure_for_user(
            self.cliente_user,
            defaults={"direccion": "Calle 10 # 15-20", "telefono": "3001234567"},
        )
        self.unidad = UnidadMedida.objects.create(
            codigo="UND",
            nombre="Unidad",
            abreviatura="und",
            descripcion="Unidad simple",
            activa=True,
            orden=1,
        )
        self.catalogo = Catalogo.objects.create(nombre_empresa="Constru-Trans")
        self.material_26k = MaterialConstruccion.objects.create(
            catalogo=self.catalogo,
            unidad_medida=self.unidad,
            nombre="Cemento Gris",
            descripcion="Bolsa 50kg",
            precio_referencia=Decimal("26000.00"),
            stock=100,
            estado="activo",
            activo=True,
        )
        self.stock_26k = Stock.objects.create(material=self.material_26k, cantidad_actual=100)

        self.material_36k = MaterialConstruccion.objects.create(
            catalogo=self.catalogo,
            unidad_medida=self.unidad,
            nombre="Varilla Corrugada",
            descripcion="Varilla 1/2",
            precio_referencia=Decimal("36000.00"),
            stock=100,
            estado="activo",
            activo=True,
        )
        self.stock_36k = Stock.objects.create(material=self.material_36k, cantidad_actual=100)

    def test_envio_duitama_tarifa_cero(self):
        self.client.force_login(self.cliente_user)
        resp = self.client.post(
            reverse("clientes:crear_pedido"),
            data={
                "material_id[]": [str(self.material_26k.cod_material)],
                "cantidad[]": ["2"],
                "ciudad": "Duitama",
                "direccion_detalle": "Calle 10 # 15-20",
            },
        )
        pedido = Pedido.objects.get(usuario=self.cliente_user)
        self.assertRedirects(
            resp,
            reverse("pagos:registrar_pago_pedido", args=[pedido.codigo_pedido]),
            fetch_redirect_response=False,
        )
        self.assertEqual(pedido.subtotal, Decimal("52000.00"))
        self.assertEqual(pedido.tarifa_envio, Decimal("0.00"))
        self.assertEqual(pedido.total, Decimal("52000.00"))
        self.assertEqual(pedido.precio, Decimal("52000.00"))

    def test_envio_otro_destino_suma_tarifa_15000_y_pago_la_incluye(self):
        self.client.force_login(self.cliente_user)
        resp = self.client.post(
            reverse("clientes:crear_pedido"),
            data={
                "material_id[]": [str(self.material_26k.cod_material)],
                "cantidad[]": ["2"],
                "ciudad": "Sogamoso",
                "direccion_detalle": "Carrera 11 # 8-12",
            },
        )
        pedido = Pedido.objects.get(usuario=self.cliente_user)
        self.assertRedirects(
            resp,
            reverse("pagos:registrar_pago_pedido", args=[pedido.codigo_pedido]),
            fetch_redirect_response=False,
        )
        self.assertEqual(pedido.subtotal, Decimal("52000.00"))
        self.assertEqual(pedido.tarifa_envio, Decimal("15000.00"))
        self.assertEqual(pedido.total, Decimal("67000.00"))

        resp_pago = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[pedido.codigo_pedido]),
            data={"metodo": "contraentrega"},
        )
        self.assertEqual(resp_pago.status_code, 302)
        pago = Pago.objects.get(pedido=pedido)
        self.assertEqual(pago.monto, Decimal("67000.00"))

    def test_pedido_menor_a_50000_duitama_no_avanza_al_pago(self):
        self.client.force_login(self.cliente_user)
        resp = self.client.post(
            reverse("clientes:crear_pedido"),
            data={
                "material_id[]": [str(self.material_26k.cod_material)],
                "cantidad[]": ["1"],
                "ciudad": "Duitama",
                "direccion_detalle": "Calle 10 # 15-20",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "50.000,00")
        self.assertEqual(Pedido.objects.count(), 0)
        self.stock_26k.refresh_from_db()
        self.assertEqual(self.stock_26k.cantidad_actual, 100)

    def test_pedido_menor_a_50000_con_envio_externo_no_avanza(self):
        self.client.force_login(self.cliente_user)
        # 26.000 + 15.000 = 41.000 < 50.000
        resp = self.client.post(
            reverse("clientes:crear_pedido"),
            data={
                "material_id[]": [str(self.material_26k.cod_material)],
                "cantidad[]": ["1"],
                "ciudad": "Sogamoso",
                "direccion_detalle": "Calle 5 # 4-10",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "50.000,00")
        self.assertEqual(Pedido.objects.count(), 0)
        self.stock_26k.refresh_from_db()
        self.assertEqual(self.stock_26k.cantidad_actual, 100)

    def test_pedido_con_envio_externo_que_alcanza_50000_si_avanza(self):
        self.client.force_login(self.cliente_user)
        # 36.000 + 15.000 = 51.000 >= 50.000
        resp = self.client.post(
            reverse("clientes:crear_pedido"),
            data={
                "material_id[]": [str(self.material_36k.cod_material)],
                "cantidad[]": ["1"],
                "ciudad": "Paipa",
                "direccion_detalle": "Carrera 20 # 10-05",
            },
        )
        pedido = Pedido.objects.get(usuario=self.cliente_user)
        self.assertRedirects(
            resp,
            reverse("pagos:registrar_pago_pedido", args=[pedido.codigo_pedido]),
            fetch_redirect_response=False,
        )
        self.assertEqual(pedido.tarifa_envio, Decimal("15000.00"))
        self.assertEqual(pedido.total, Decimal("51000.00"))

    def test_editar_pedido_por_debajo_del_minimo_bloqueado_y_cambio_ciudad_actualiza_total(self):
        self.client.force_login(self.cliente_user)
        self.client.post(
            reverse("clientes:crear_pedido"),
            data={
                "material_id[]": [str(self.material_26k.cod_material)],
                "cantidad[]": ["2"],
                "ciudad": "Duitama",
                "direccion_detalle": "Calle 10 # 15-20",
            },
        )
        pedido = Pedido.objects.get(usuario=self.cliente_user)
        url_editar = reverse("clientes:editar_pedido", args=[pedido.codigo_pedido])

        # Intentar bajar a 1 unidad en Duitama (26.000 < 50.000) -> bloqueado
        resp_invalido = self.client.post(
            url_editar,
            data={
                "material_id[]": [str(self.material_26k.cod_material)],
                "cantidad[]": ["1"],
                "ciudad": "Duitama",
                "direccion_detalle": "Calle 10 # 15-20",
            },
        )
        self.assertEqual(resp_invalido.status_code, 200)
        self.assertContains(resp_invalido, "50.000,00")
        pedido.refresh_from_db()
        self.assertEqual(pedido.total, Decimal("52000.00"))

        # Cambiar ciudad a Sogamoso manteniendo 2 unidades -> 52.000 + 15.000 = 67.000
        resp_valido = self.client.post(
            url_editar,
            data={
                "material_id[]": [str(self.material_26k.cod_material)],
                "cantidad[]": ["2"],
                "ciudad": "Sogamoso",
                "direccion_detalle": "Calle 10 # 15-20",
            },
        )
        self.assertEqual(resp_valido.status_code, 302)
        pedido.refresh_from_db()
        self.assertEqual(pedido.tarifa_envio, Decimal("15000.00"))
        self.assertEqual(pedido.total, Decimal("67000.00"))

