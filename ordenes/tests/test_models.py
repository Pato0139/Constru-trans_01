from django.test import TestCase

from ordenes.models import DetallePedido, Entrega, Pedido
from usuarios.models import MaterialConstruccion, UnidadMedida, Usuario, Vehiculo


class OrdenesModelsTests(TestCase):
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
        self.conductor = Usuario.objects.create_user(
            username="conductororden",
            email="conductororden@test.com",
            password="password123",
            nombres="Conductor",
            apellidos="Orden",
            documento="654654654",
            tipo_documento="CC",
            rol="conductor",
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
        self.vehiculo = Vehiculo.objects.create(
            placa="AAA111",
            marca="Toyota",
            modelo="2020",
            tipo_vehiculo="Camión",
            capacidad_carga=10.0,
            estado="disponible",
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

    def test_crear_entrega(self):
        pedido = Pedido.objects.create(
            usuario=self.cliente,
            direccion_destino="Tunja, Calle 2",
            estado="pendiente",
        )
        entrega = Entrega.objects.create(
            pedido=pedido,
            conductor=self.conductor,
            vehiculo=self.vehiculo,
            direccion_entrega="Tunja, Calle 2",
            estado="pendiente",
        )
        self.assertEqual(entrega.pedido, pedido)
        self.assertEqual(entrega.vehiculo, self.vehiculo)
        self.assertEqual(entrega.estado, "pendiente")
