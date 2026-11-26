from django.test import TestCase

from apps.catalogo.models import MaterialConstruccion, Stock, UnidadMedida
from apps.catalogo.services.kardex import calcular_nivel_alerta_stock
from apps.usuarios.models import Notificacion, Usuario


class AlertasStockTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="admin-stock@test.com",
            email="admin-stock@test.com",
            password="password123",
            nombres="Admin",
            apellidos="Stock",
            rol="admin",
        )
        self.unidad = UnidadMedida.objects.create(
            codigo="UND", nombre="Unidad", abreviatura="und"
        )
        self.material = MaterialConstruccion.objects.create(
            nombre="Ladrillo común",
            unidad_medida=self.unidad,
            descripcion="Material de prueba",
            precio_referencia=1000,
        )

    def guardar_stock_y_procesar_commit(self, stock):
        with self.captureOnCommitCallbacks(execute=True):
            stock.save()

    def test_nivel_alerta_usa_minimo_individual_y_critico_al_cincuenta_por_ciento(self):
        self.assertEqual(calcular_nivel_alerta_stock(101, 100), "suficiente")
        self.assertEqual(calcular_nivel_alerta_stock(100, 100), "bajo")
        self.assertEqual(calcular_nivel_alerta_stock(51, 100), "bajo")
        self.assertEqual(calcular_nivel_alerta_stock(50, 100), "critico")
        self.assertEqual(calcular_nivel_alerta_stock(0, 0), "critico")

    def test_alerta_se_actualiza_se_resuelve_y_se_reabre_sin_duplicarse(self):
        stock = Stock.objects.create(
            material=self.material,
            cantidad_actual=101,
            stock_minimo=100,
            ubicacion="Bodega",
        )
        self.assertEqual(Notificacion.objects.filter(usuario=self.admin).count(), 0)

        stock.cantidad_actual = 100
        self.guardar_stock_y_procesar_commit(stock)
        alerta = Notificacion.objects.get(usuario=self.admin)
        alerta_id = alerta.pk
        self.assertEqual(alerta.tipo, "warning")
        self.assertIn("100 und", alerta.mensaje)
        self.assertIn("mínimo: 100 und", alerta.mensaje)
        self.assertIn("Ladrillo común", alerta.mensaje)
        self.assertTrue(alerta.link)

        alerta.leida = True
        alerta.save(update_fields=["leida"])
        stock.cantidad_actual = 80
        self.guardar_stock_y_procesar_commit(stock)
        self.assertEqual(Notificacion.objects.filter(usuario=self.admin).count(), 1)
        alerta.refresh_from_db()
        self.assertTrue(alerta.leida)
        self.assertIn("80 und", alerta.mensaje)

        stock.cantidad_actual = 50
        self.guardar_stock_y_procesar_commit(stock)
        alerta.refresh_from_db()
        self.assertEqual(alerta.tipo, "danger")
        self.assertFalse(alerta.leida)
        self.assertEqual(Notificacion.objects.filter(usuario=self.admin).count(), 1)

        stock.cantidad_actual = 101
        self.guardar_stock_y_procesar_commit(stock)
        alerta.refresh_from_db()
        self.assertEqual(alerta.tipo, "success")
        self.assertTrue(alerta.leida)

        stock.cantidad_actual = 100
        self.guardar_stock_y_procesar_commit(stock)
        alerta.refresh_from_db()
        self.assertEqual(alerta.pk, alerta_id)
        self.assertEqual(alerta.tipo, "warning")
        self.assertFalse(alerta.leida)
        self.assertEqual(Notificacion.objects.filter(usuario=self.admin).count(), 1)
