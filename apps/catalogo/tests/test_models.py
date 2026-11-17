from django.db.models import F
from django.test import TestCase

from apps.catalogo.forms import MarcaForm, MaterialForm
from apps.catalogo.models import MARCAS_MATERIAL, Marca, MaterialConstruccion, Stock, UnidadMedida


class CatalogoModelsTests(TestCase):
    def test_crear_unidad_medida(self):
        unidad = UnidadMedida.objects.create(
            codigo="M3", nombre="Metros cúbicos", abreviatura="m3", activa=True
        )
        self.assertEqual(unidad.codigo, "M3")
        self.assertEqual(unidad.abreviatura, "m3")

    def test_crear_material(self):
        unidad = UnidadMedida.objects.create(codigo="M3", nombre="Metros cúbicos", abreviatura="m3")
        material = MaterialConstruccion.objects.create(
            nombre="Arena",
            unidad_medida=unidad,
            descripcion="Arena gruesa",
            precio_referencia=50000,
        )
        self.assertEqual(material.nombre, "Arena")
        self.assertEqual(material.unidad_medida, unidad)

    def test_crear_stock(self):
        unidad = UnidadMedida.objects.create(codigo="M3", nombre="Metros cúbicos", abreviatura="m3")
        material = MaterialConstruccion.objects.create(
            nombre="Arena",
            unidad_medida=unidad,
            descripcion="Arena gruesa",
            precio_referencia=50000,
        )
        stock = Stock.objects.create(
            material=material, cantidad_actual=100, stock_minimo=10, ubicacion="Almacén 1"
        )
        self.assertEqual(stock.material, material)
        self.assertEqual(stock.cantidad_actual, 100)
        self.assertEqual(stock.id, material.cod_material)

    def test_stock_con_actualizacion_atomica_sincroniza_material(self):
        unidad = UnidadMedida.objects.create(
            codigo="UND",
            nombre="Unidad",
            abreviatura="u",
        )
        material = MaterialConstruccion.objects.create(
            nombre="Bloque",
            unidad_medida=unidad,
            descripcion="Bloque de prueba",
            precio_referencia=5000,
        )
        stock = Stock.objects.create(material=material, cantidad_actual=4)

        stock.cantidad_actual = F("cantidad_actual") + 3
        stock.save()

        material.refresh_from_db()
        stock.refresh_from_db()
        self.assertEqual(stock.cantidad_actual, 7)
        self.assertEqual(material.stock, 7)

    def test_formulario_material_crea_stock_y_ubicacion(self):
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

    def test_material_dropdown_muestra_marcas_conocidas_y_omite_marcas_invalidas(self):
        Marca.objects.create(nombre="Argos")
        Marca.objects.create(nombre="Casara")

        form = MaterialForm()
        choices = dict(form.fields["marca_nombre"].choices)

        self.assertTrue(set(MARCAS_MATERIAL).issubset(choices))
        self.assertNotIn("Casara", choices)

    def test_editar_material_reemplaza_marca_no_aprobada_por_una_conocida(self):
        unidad = UnidadMedida.objects.create(
            codigo="UND",
            nombre="Unidad",
            abreviatura="u",
        )
        marca_no_aprobada = Marca.objects.create(nombre="444444444Argos")
        marca_conocida = Marca.objects.create(nombre="Argos")
        material = MaterialConstruccion.objects.create(
            nombre="Arena",
            unidad_medida=unidad,
            descripcion="Arena para construcción",
            precio_referencia=25000,
            marca=marca_no_aprobada,
        )

        form = MaterialForm(
            data={
                "nombre": material.nombre,
                "unidad_medida": unidad.pk,
                "descripcion": material.descripcion,
                "precio_referencia": "25000.00",
                "marca_nombre": "Argos",
            },
            instance=material,
        )

        self.assertTrue(form.is_valid(), form.errors)
        material = form.save()
        self.assertEqual(material.marca, marca_conocida)

    def test_material_rechaza_marca_no_aprobada_en_post(self):
        unidad = UnidadMedida.objects.create(
            codigo="UND",
            nombre="Unidad",
            abreviatura="u",
        )
        Marca.objects.create(nombre="444444444")

        form = MaterialForm(
            data={
                "nombre": "Arena",
                "unidad_medida": unidad.pk,
                "descripcion": "Arena para construcción",
                "precio_referencia": "25000.00",
                "marca_nombre": "444444444",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("marca_nombre", form.errors)

    def test_formulario_de_marcas_permite_registrar_solo_opciones_conocidas(self):
        marca_invalida = MarcaForm(data={"nombre": "Casara"})
        marca_conocida = MarcaForm(data={"nombre": "Argos"})

        self.assertFalse(marca_invalida.is_valid())
        self.assertTrue(marca_conocida.is_valid(), marca_conocida.errors)
        self.assertEqual(marca_conocida.save().nombre, "Argos")

        opciones = dict(MarcaForm().fields["nombre"].choices)
        self.assertNotIn("Argos", opciones)
