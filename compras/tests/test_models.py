from django.test import TestCase

from compras.models import Compra, DetalleCompra
from usuarios.models import MaterialConstruccion, Proveedor, UnidadMedida, Usuario


class ComprasModelsTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="admincompras",
            email="compras@test.com",
            password="password123",
            nombres="Admin",
            apellidos="Compras",
            documento="123123123",
            tipo_documento="CC",
            rol="admin",
        )
        self.unidad = UnidadMedida.objects.create(
            codigo="UND",
            nombre="Unidad",
            abreviatura="u",
        )
        self.material = MaterialConstruccion.objects.create(
            nombre="Cemento",
            unidad_medida=self.unidad,
            descripcion="Bulto de cemento",
            precio_referencia=30000,
        )
        self.proveedor = Proveedor.objects.create(
            nombre_empresa="Proveedor SAS",
            nit="9000000000",
            telefono="3201234567",
            correo="proveedor@test.com",
        )

    def test_compra_calcula_total_desde_detalles(self):
        compra = Compra.objects.create(
            proveedor=self.proveedor,
            usuario=self.usuario,
        )
        DetalleCompra.objects.create(
            compra=compra,
            material=self.material,
            cantidad=3,
            precio_unitario=30000,
        )
        compra.refresh_from_db()
        self.assertEqual(float(compra.total_compra), 90000.0)

    def test_detalle_compra_subtotal(self):
        compra = Compra.objects.create(
            proveedor=self.proveedor,
            usuario=self.usuario,
        )
        detalle = DetalleCompra.objects.create(
            compra=compra,
            material=self.material,
            cantidad=2,
            precio_unitario=25000,
        )
        self.assertEqual(float(detalle.subtotal), 50000.0)
