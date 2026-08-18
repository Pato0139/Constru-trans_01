from django.test import TestCase
from usuarios.forms import MaterialForm
from usuarios.models import UnidadMedida, MaterialConstruccion, Stock


class InventarioModelsTests(TestCase):
    def test_crear_unidad_medida(self):
        """Prueba crear una unidad de medida"""
        unidad = UnidadMedida.objects.create(
            codigo="M3",
            nombre="Metros cúbicos",
            abreviatura="m3",
            activa=True
        )
        self.assertEqual(unidad.codigo, "M3")
        self.assertEqual(unidad.abreviatura, "m3")

    def test_crear_material(self):
        """Prueba crear un material de construcción"""
        unidad = UnidadMedida.objects.create(
            codigo="M3",
            nombre="Metros cúbicos",
            abreviatura="m3"
        )
        material = MaterialConstruccion.objects.create(
            nombre="Arena",
            unidad_medida=unidad,
            descripcion="Arena gruesa",
            precio_referencia=50000
        )
        self.assertEqual(material.nombre, "Arena")
        self.assertEqual(material.unidad_medida, unidad)

    def test_crear_stock(self):
        """Prueba crear stock para un material"""
        unidad = UnidadMedida.objects.create(
            codigo="M3",
            nombre="Metros cúbicos",
            abreviatura="m3"
        )
        material = MaterialConstruccion.objects.create(
            nombre="Arena",
            unidad_medida=unidad,
            descripcion="Arena gruesa",
            precio_referencia=50000
        )
        stock = Stock.objects.create(
            material=material,
            cantidad_actual=100,
            stock_minimo=10,
            ubicacion="Almacén 1"
        )
        self.assertEqual(stock.material, material)
        self.assertEqual(stock.cantidad_actual, 100)
        self.assertEqual(stock.id, material.cod_material)

    def test_formulario_material_crea_stock_y_ubicacion(self):
        """El formulario del catálogo crea el material y su stock inicial."""
        unidad = UnidadMedida.objects.create(
            codigo="UND",
            nombre="Unidad",
            abreviatura="u",
        )

        form = MaterialForm(
            data={
                "nombre": "Piedra triturada",
                "unidad_medida": unidad.pk,
                "descripcion": "Material de prueba",
                "precio_referencia": "25000.00",
                "stock": 7,
                "ubicacion": "Bodega QA",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        material = form.save()

        self.assertEqual(material.stock_info.cantidad_actual, 7)
        self.assertEqual(material.stock_info.ubicacion, "Bodega QA")
