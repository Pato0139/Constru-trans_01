from django.test import TestCase
from django.urls import reverse

from apps.catalogo.models import MaterialConstruccion, MovimientoInventario, Stock, UnidadMedida
from apps.compras.models import Proveedor, ProveedorMaterial
from apps.usuarios.models import Usuario


class EntradaInventarioProveedorTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="admin-entrada@test.com",
            email="admin-entrada@test.com",
            password="password123",
            nombres="Admin",
            apellidos="Inventario",
            rol="admin",
        )
        self.proveedor = Proveedor.objects.create(
            nombre_empresa="Proveedor Prueba",
            nit="900123456",
            telefono="3001234567",
        )
        unidad = UnidadMedida.objects.create(
            codigo="UND", nombre="Unidad", abreviatura="und"
        )
        self.material = MaterialConstruccion.objects.create(
            nombre="Ladrillo rojo",
            unidad_medida=unidad,
            descripcion="Material de prueba",
            precio_referencia=1000,
        )
        Stock.objects.create(material=self.material, cantidad_actual=20000, stock_minimo=1000)
        self.client.force_login(self.admin)

    def test_entrada_desde_catalogo_de_proveedor_actualiza_stock_y_kardex(self):
        response = self.client.post(
            reverse(
                "compras:catalogo_proveedor",
                args=[self.proveedor.codigo_proveedor],
            ),
            {
                "catalogo-TOTAL_FORMS": "1",
                "catalogo-INITIAL_FORMS": "0",
                "catalogo-MIN_NUM_FORMS": "0",
                "catalogo-MAX_NUM_FORMS": "1000",
                "catalogo-0-material": str(self.material.pk),
                "catalogo-0-precio_actual": "1000",
                "catalogo-0-referencia_proveedor": "REF-1",
                "catalogo-0-observaciones": "Recepción de prueba",
                "catalogo-0-activo": "on",
                "catalogo-0-cantidad_recibida": "50000",
            },
        )

        self.assertEqual(response.status_code, 302)
        stock = Stock.objects.get(material=self.material)
        self.assertEqual(stock.cantidad_actual, 70000)
        self.assertEqual(
            MovimientoInventario.objects.filter(
                material=self.material, tipo_movimiento="entrada", cantidad=50000
            ).count(),
            1,
        )
        self.assertTrue(
            ProveedorMaterial.objects.filter(
                proveedor=self.proveedor, material=self.material
            ).exists()
        )

    def test_entrada_en_producto_ya_vinculado_al_proveedor_actualiza_stock(self):
        oferta = ProveedorMaterial.objects.create(
            proveedor=self.proveedor,
            material=self.material,
            precio_actual=1000,
        )
        response = self.client.post(
            reverse(
                "compras:catalogo_proveedor",
                args=[self.proveedor.codigo_proveedor],
            ),
            {
                "catalogo-TOTAL_FORMS": "1",
                "catalogo-INITIAL_FORMS": "1",
                "catalogo-MIN_NUM_FORMS": "0",
                "catalogo-MAX_NUM_FORMS": "1000",
                "catalogo-0-id": str(oferta.pk),
                "catalogo-0-material": str(self.material.pk),
                "catalogo-0-precio_actual": "1000",
                "catalogo-0-referencia_proveedor": "REF-2",
                "catalogo-0-observaciones": "Reposición de prueba",
                "catalogo-0-activo": "on",
                "catalogo-0-cantidad_recibida": "50000",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Stock.objects.get(material=self.material).cantidad_actual, 70000)
        self.assertEqual(
            MovimientoInventario.objects.filter(
                material=self.material, tipo_movimiento="entrada", cantidad=50000
            ).count(),
            1,
        )
