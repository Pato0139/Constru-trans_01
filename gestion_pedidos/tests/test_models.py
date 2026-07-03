from django.test import TestCase

from gestion_pedidos.models import DetalleSolicitudPedido, SolicitudPedido
from usuarios.models import MaterialConstruccion, UnidadMedida, Usuario


class GestionPedidosModelsTests(TestCase):
    def setUp(self):
        self.cliente = Usuario.objects.create_user(
            username="clientegestion",
            email="clientegestion@test.com",
            password="password123",
            nombres="Cliente",
            apellidos="Gestion",
            documento="999888777",
            tipo_documento="CC",
            rol="cliente",
        )
        self.unidad = UnidadMedida.objects.create(
            codigo="KG",
            nombre="Kilogramo",
            abreviatura="kg",
        )
        self.material = MaterialConstruccion.objects.create(
            nombre="Grava",
            unidad_medida=self.unidad,
            descripcion="Grava gris",
            precio_referencia=10000,
        )

    def test_detalle_solicitud_toma_precio_del_material(self):
        pedido = SolicitudPedido.objects.create(
            cliente=self.cliente,
            descuento=0,
        )
        detalle = DetalleSolicitudPedido.objects.create(
            pedido=pedido,
            material=self.material,
            cantidad=3,
            precio_unitario=0,  # save() lo reemplaza por material.precio
        )
        self.assertEqual(float(detalle.precio_unitario), 10000.0)
        pedido.refresh_from_db()
        self.assertEqual(float(pedido.total), 30000.0)

    def test_calcular_total_aplica_descuento(self):
        pedido = SolicitudPedido.objects.create(
            cliente=self.cliente,
            descuento=5000,
        )
        DetalleSolicitudPedido.objects.create(
            pedido=pedido,
            material=self.material,
            cantidad=2,
            precio_unitario=0,
        )
        pedido.refresh_from_db()
        self.assertEqual(float(pedido.total), 15000.0)
