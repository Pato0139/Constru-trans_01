from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.usuarios.models import Usuario, Material
from .models import Orden, DetalleOrden

User = get_user_model()


class CalcularTotalTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='admin1234')
        self.usuario = Usuario.objects.create(
            user=self.user,
            nombres='Admin',
            apellidos='Test',
            rol='admin'
        )
        self.material = Material.objects.create(
            nombre='Cemento',
            tipo='Cemento',
            precio=25000,
            stock=100
        )
        self.orden = Orden.objects.create(
            cliente=self.usuario,
            direccion_origen='Calle 1',
            direccion_destino='Calle 2',
        )

    # CT-273 — Multiplicar cantidad x precio
    def test_subtotal_detalle(self):
        detalle = DetalleOrden.objects.create(
            orden=self.orden,
            material=self.material,
            cantidad=3,
            precio_unitario=25000
        )
        self.assertEqual(detalle.subtotal(), 75000)

    # CT-272 CT-323 — Suma de subtotales
    def test_calcular_total_suma_detalles(self):
        DetalleOrden.objects.create(
            orden=self.orden, material=self.material,
            cantidad=2, precio_unitario=25000
        )
        DetalleOrden.objects.create(
            orden=self.orden, material=self.material,
            cantidad=1, precio_unitario=10000
        )
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.precio, 60000)

    # CT-324 — Total se actualiza al agregar material
    def test_total_actualiza_al_agregar(self):
        DetalleOrden.objects.create(
            orden=self.orden, material=self.material,
            cantidad=4, precio_unitario=5000
        )
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.precio, 20000)

    # CT-325 — Total se actualiza al eliminar material
    def test_total_actualiza_al_eliminar(self):
        detalle = DetalleOrden.objects.create(
            orden=self.orden, material=self.material,
            cantidad=2, precio_unitario=10000
        )
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.precio, 20000)
        detalle.delete()
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.precio, 0)

    # CT-276 — Total no puede ser negativo
    def test_total_no_negativo(self):
        total = self.orden.calcular_total()
        self.assertGreaterEqual(total, 0)

    # CT-327 — Total se guarda en BD
    def test_total_guardado_en_bd(self):
        DetalleOrden.objects.create(
            orden=self.orden, material=self.material,
            cantidad=1, precio_unitario=30000
        )
        orden_db = Orden.objects.get(id=self.orden.id)
        self.assertEqual(orden_db.precio, 30000)

    # CT-328 — Endpoint total
    def test_endpoint_total(self):
        self.client.login(username='admin', password='admin1234')
        DetalleOrden.objects.create(
            orden=self.orden, material=self.material,
            cantidad=2, precio_unitario=15000
        )
        url = reverse('ordenes:api_total_orden', args=[self.orden.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total'], '30000.00')