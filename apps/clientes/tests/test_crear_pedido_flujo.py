from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.catalogo.models import Catalogo, MaterialConstruccion, Stock, UnidadMedida
from apps.clientes.models import Cliente
from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.usuarios.models import Usuario


class CrearPedidoFlujoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cliente_user = Usuario.objects.create_user(
            username="cliente_test",
            email="cliente_test@constru-trans.com",
            password="Password123!",
            nombres="Juan",
            apellidos="Pérez",
            documento="1010202030",
            tipo_documento="CC",
            rol="cliente",
        )
        self.cliente_profile, _ = Cliente.ensure_for_user(
            self.cliente_user,
            defaults={"direccion": "Calle 10 # 20-30", "telefono": "3001234567"},
        )
        self.admin_user = Usuario.objects.create_user(
            username="admin_test",
            email="admin_test@constru-trans.com",
            password="Password123!",
            nombres="Carlos",
            apellidos="Admin",
            documento="9090808070",
            tipo_documento="CC",
            rol="admin",
            is_staff=True,
        )

        self.unidad = UnidadMedida.objects.create(
            codigo="UND",
            nombre="Unidad",
            abreviatura="und",
            descripcion="Unidad simple",
            activa=True,
            orden=1,
        )
        self.catalogo = Catalogo.objects.create(nombre_empresa="Constru-Trans Materiales")
        self.material = MaterialConstruccion.objects.create(
            catalogo=self.catalogo,
            unidad_medida=self.unidad,
            nombre="Cemento Gris Especial",
            descripcion="Bolsa de cemento 50kg",
            precio_referencia=Decimal("26000.00"),
            stock=100,
            estado="activo",
            activo=True,
        )
        self.stock = Stock.objects.create(
            material=self.material,
            cantidad_actual=100,
        )

    def test_flujo_completo_pedido_y_pago(self):
        """Flujo completo: cliente crea pedido -> registra pago -> admin y cliente ven el estado."""
        self.client.force_login(self.cliente_user)

        # 1. Cliente crea el pedido
        response_crear = self.client.post(
            reverse("clientes:crear_pedido"),
            data={
                "material_id[]": [str(self.material.cod_material)],
                "cantidad[]": ["2"],
                "ciudad": "Bogotá",
                "direccion_detalle": "Carrera 7 # 72-41",
            },
        )
        self.assertEqual(response_crear.status_code, 302)

        pedido = Pedido.objects.first()
        self.assertIsNotNone(pedido)
        self.assertEqual(pedido.usuario, self.cliente_user)
        self.assertEqual(pedido.total, Decimal("52000.00"))
        self.assertEqual(pedido.subtotal, Decimal("52000.00"))
        self.assertEqual(pedido.estado, "pendiente")

        # 2. Cliente registra el pago
        response_pago = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[pedido.codigo_pedido]),
            data={
                "metodo": "contraentrega",
            },
        )
        self.assertEqual(response_pago.status_code, 302)

        pago = Pago.objects.filter(pedido=pedido).first()
        self.assertIsNotNone(pago)
        self.assertEqual(pago.estado, "pendiente")
        self.assertEqual(pago.monto, Decimal("52000.00"))

        # 3. Cliente ve el pedido en su panel como "Pendiente"
        response_cliente = self.client.get(reverse("clientes:mis_pedidos"))
        self.assertEqual(response_cliente.status_code, 200)
        self.assertContains(response_cliente, f"#{pedido.codigo_pedido}")

        # 4. Administrador ve el pedido en su lista de órdenes
        self.client.force_login(self.admin_user)
        response_admin = self.client.get(reverse("pedidos:lista_pedidos_admin"))
        self.assertEqual(response_admin.status_code, 200)
        self.assertContains(response_admin, str(pedido.codigo_pedido))
