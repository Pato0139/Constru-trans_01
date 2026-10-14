from django.test import TestCase

from apps.catalogo.models as  (
    MaterialConstruccion,
    MovimientoInventario,
    Stock,
    UnidadMedida,
)
from apps.catalogo.services.kardex import KardexService


class CatalogoStockTests(TestCase):
    def setUp(self):
        self.unidad = UnidadMedida.objects.create(
            codigo="UND",
            nombre="Unidad",
            abreviatura="u",
        )
        self.material = MaterialConstruccion.objects.create(
            nombre="Ladrillo",
            unidad_medida=self.unidad,
            descripcion="Ladrillo rojo",
            precio_referencia=1500,
        )
        self.stock = Stock.objects.create(
            material=self.material,
            cantidad_actual=10,
            stock_minimo=2,
            ubicacion="Bodega A",
        )

    def test_registrar_entrada_incrementa_stock(self):
        KardexService.registrar_movimiento(
            material_id=self.material.pk,
            tipo="entrada",
            cantidad=5,
            observacion="Ingreso de prueba",
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad_actual, 15)

    def test_registrar_salida_decrementa_stock(self):
        KardexService.registrar_movimiento(
            material_id=self.material.pk,
            tipo="salida",
            cantidad=4,
            observacion="Salida de prueba",
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad_actual, 6)

    def test_salida_rechaza_stock_insuficiente(self):
        with self.assertRaises(ValueError):
            KardexService.registrar_movimiento(
                material_id=self.material.pk,
                tipo="salida",
                cantidad=999,
                observacion="Prueba de error",
            )

    def test_movimiento_con_material_huerfano_conserva_el_codigo_original(self):
        movimiento = MovimientoInventario.objects.create(
            material=None,
            material_codigo_original=152,
            tipo_movimiento="entrada",
            cantidad=1,
            observacion="Registro histórico",
        )

        self.assertEqual(
            movimiento.material_label,
            "Material no disponible (código 152)",
        )
        self.assertEqual(
            str(movimiento),
            "ENTRADA: 1 de Material no disponible (código 152)",
        )
