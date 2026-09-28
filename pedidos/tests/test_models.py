from django.test import TestCase

from catalogo.models import MaterialConstruccion, UnidadMedida
from pedidos.models import DetallePedido, Pedido
from usuarios.models import Usuario


class PedidosModelsTests(TestCase):
    def setUp(self):
        self.cliente = Usuario.objects.create_user(
            username="clienteorden",
            email="clienteorden@test.com",
            password="password123",
            nombres="Cliente",
            apellidos="Orden",
            documento="321321321",
            tipo_documento="CC",
            rol="cliente",
        )
        self.unidad = UnidadMedida.objects.create(
            codigo="M3",
            nombre="Metro cúbico",
            abreviatura="m3",
        )
        self.material = MaterialConstruccion.objects.create(
            nombre="Arena",
            unidad_medida=self.unidad,
            descripcion="Arena fina",
            precio_referencia=50000,
        )

    def test_detalle_pedido_recalcula_total(self):
        pedido = Pedido.objects.create(
            usuario=self.cliente,
            direccion_destino="Tunja, Calle 1",
            estado="pendiente",
        )
        DetallePedido.objects.create(
            pedido=pedido,
            material=self.material,
            cantidad=4,
            precio_unitario=50000,
        )
        pedido.refresh_from_db()
        self.assertEqual(float(pedido.total), 200000.0)
        self.assertEqual(float(pedido.precio), 200000.0)
