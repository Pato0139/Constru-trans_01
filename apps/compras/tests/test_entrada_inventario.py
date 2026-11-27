import uuid

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.catalogo.models import HistorialPrecioMaterial, MaterialConstruccion, MovimientoInventario, Stock, UnidadMedida
from apps.compras.models import Compra, DetalleCompra, Proveedor, ProveedorMaterial
from apps.usuarios.models import Usuario


@override_settings(DATABASE_ROUTERS=[], OFFLINE_MODE=False)
class EntradaInventarioProveedorTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="admin-entrada@test.com", email="admin-entrada@test.com", password="password123",
            nombres="Admin", apellidos="Inventario", rol="admin",
        )
        self.proveedor = Proveedor.objects.create(
            nombre_empresa="Proveedor Prueba", nit="900123456", telefono="3001234567",
        )
        self.otro_proveedor = Proveedor.objects.create(
            nombre_empresa="Otro Proveedor", nit="900123457", telefono="3001234568",
        )
        unidad = UnidadMedida.objects.create(codigo="UND", nombre="Unidad", abreviatura="und")
        self.material = MaterialConstruccion.objects.create(
            nombre="Ladrillo común", unidad_medida=unidad, descripcion="Material de prueba",
            precio_referencia=1000,
        )
        Stock.objects.create(material=self.material, cantidad_actual=7000, stock_minimo=1000)
        ProveedorMaterial.objects.create(proveedor=self.proveedor, material=self.material, precio_actual=800)
        self.client.force_login(self.admin)

    def payload(self, token=None, **line_fields):
        data = {
            "clave_idempotencia": str(token or uuid.uuid4()),
            "proveedor": str(self.proveedor.pk),
            "fecha_compra": "2026-11-27T10:30",
            "numero_factura": "FAC-001",
            "observaciones": "Recepción de materiales",
            "detalles-TOTAL_FORMS": "1",
            "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "1",
            "detalles-MAX_NUM_FORMS": "1000",
            "detalles-0-material": str(self.material.pk),
            "detalles-0-cantidad": "50000",
            "detalles-0-precio_unitario": "800",
            "detalles-0-precio_venta_unitario": "1000",
        }
        data.update(line_fields)
        return data

    def test_entrada_actualiza_stock_y_guarda_kardex_e_historial(self):
        response = self.client.post(reverse("compras:crear_compra"), self.payload())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Stock.objects.get(material=self.material).cantidad_actual, 57000)
        compra = Compra.objects.get(proveedor=self.proveedor)
        detalle = DetalleCompra.objects.get(compra=compra)
        movimiento = MovimientoInventario.objects.get(compra=compra)
        self.assertEqual(compra.estado, "recibida")
        self.assertEqual(compra.numero_factura, "FAC-001")
        self.assertEqual(compra.total_compra, 40_000_000)
        self.assertEqual(detalle.precio_unitario, 800)
        self.assertEqual(detalle.precio_venta_unitario, 1000)
        self.assertEqual(detalle.material_nombre, "Ladrillo común")
        self.assertEqual(detalle.unidad_medida_abreviatura, "und")
        self.assertEqual(movimiento.stock_anterior, 7000)
        self.assertEqual(movimiento.stock_posterior, 57000)
        self.assertEqual(movimiento.usuario, self.admin)
        self.material.refresh_from_db()
        self.assertEqual(self.material.precio_referencia, 1000)
        self.assertEqual(self.client.get(reverse("compras:detalle_compra", args=[compra.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("compras:perfil_proveedor", args=[self.proveedor.pk])).status_code, 200)

    def test_actualizar_precio_venta_requiere_confirmacion_explicita(self):
        response = self.client.post(
            reverse("compras:crear_compra"),
            self.payload(**{"detalles-0-actualizar_precio_venta": "on", "detalles-0-precio_venta_unitario": "1200"}),
        )
        self.assertEqual(response.status_code, 302)
        self.material.refresh_from_db()
        self.assertEqual(self.material.precio_referencia, 1200)
        self.assertTrue(HistorialPrecioMaterial.objects.filter(
            material=self.material, precio_anterior=1000, precio_nuevo=1200
        ).exists())
        detalle = DetalleCompra.objects.get()
        self.assertEqual(detalle.precio_venta_unitario, 1200)

    def test_reenvio_de_la_misma_solicitud_no_duplica_la_entrada(self):
        token = uuid.uuid4()
        payload = self.payload(token)
        first = self.client.post(reverse("compras:crear_compra"), payload)
        second = self.client.post(reverse("compras:crear_compra"), payload)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(Compra.objects.count(), 1)
        self.assertEqual(MovimientoInventario.objects.filter(tipo_movimiento="entrada").count(), 1)
        self.assertEqual(Stock.objects.get(material=self.material).cantidad_actual, 57000)

    def test_dos_proveedores_pueden_suministrar_el_mismo_material(self):
        ProveedorMaterial.objects.create(proveedor=self.otro_proveedor, material=self.material, precio_actual=850)
        response = self.client.get(reverse("compras:crear_compra"), {"proveedor": self.proveedor.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.material.nombre)
        self.assertEqual(ProveedorMaterial.objects.filter(material=self.material).count(), 2)

    def test_catalogo_de_proveedor_guarda_su_costo_sin_cambiar_venta_ni_stock(self):
        ProveedorMaterial.objects.filter(proveedor=self.proveedor).delete()
        response = self.client.post(
            reverse("compras:catalogo_proveedor", args=[self.proveedor.pk]),
            {
                "catalogo-TOTAL_FORMS": "1", "catalogo-INITIAL_FORMS": "0",
                "catalogo-MIN_NUM_FORMS": "0", "catalogo-MAX_NUM_FORMS": "1000",
                "catalogo-0-material": str(self.material.pk), "catalogo-0-precio_actual": "850",
                "catalogo-0-referencia_proveedor": "REF-COSTO", "catalogo-0-observaciones": "Cotización",
                "catalogo-0-activo": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ProveedorMaterial.objects.get(proveedor=self.proveedor, material=self.material).precio_actual, 850)
        self.material.refresh_from_db()
        self.assertEqual(self.material.precio_referencia, 1000)
        self.assertEqual(Stock.objects.get(material=self.material).cantidad_actual, 7000)

    def test_anular_entrada_recibida_reversa_el_stock_y_deja_trazabilidad(self):
        self.client.post(reverse("compras:crear_compra"), self.payload())
        compra = Compra.objects.get()
        response = self.client.post(
            reverse("compras:cambiar_estado_compra", args=[compra.pk]),
            {"estado": "cancelada", "motivo_anulacion": "Factura duplicada"},
        )
        self.assertEqual(response.status_code, 302)
        compra.refresh_from_db()
        self.assertEqual(compra.estado, "cancelada")
        self.assertEqual(compra.motivo_anulacion, "Factura duplicada")
        self.assertEqual(Stock.objects.get(material=self.material).cantidad_actual, 7000)
        reversa = MovimientoInventario.objects.get(compra=compra, tipo_movimiento="salida")
        self.assertEqual(reversa.stock_anterior, 57000)
        self.assertEqual(reversa.stock_posterior, 7000)

    def test_anulacion_con_stock_insuficiente_no_deja_reversion_parcial(self):
        self.client.post(reverse("compras:crear_compra"), self.payload())
        compra = Compra.objects.get()
        stock = Stock.objects.get(material=self.material)
        stock.cantidad_actual = 10000
        stock.save()
        response = self.client.post(
            reverse("compras:cambiar_estado_compra", args=[compra.pk]),
            {"estado": "cancelada", "motivo_anulacion": "Ajuste solicitado"},
        )
        self.assertEqual(response.status_code, 302)
        compra.refresh_from_db()
        self.assertEqual(compra.estado, "recibida")
        self.assertFalse(MovimientoInventario.objects.filter(compra=compra, tipo_movimiento="salida").exists())
        self.assertEqual(Stock.objects.get(material=self.material).cantidad_actual, 10000)

    def test_material_no_asociado_se_rechaza_sin_modificar_inventario(self):
        data = self.payload()
        data["proveedor"] = str(self.otro_proveedor.pk)
        response = self.client.post(reverse("compras:crear_compra"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Compra.objects.exists())
        self.assertEqual(Stock.objects.get(material=self.material).cantidad_actual, 7000)
        self.assertFalse(MovimientoInventario.objects.exists())
