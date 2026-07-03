from django.test import TestCase
from usuarios.models import Usuario
from facturacion.models import Factura


class FacturaModelTests(TestCase):
    def test_crear_factura(self):
        """Prueba crear una factura básica"""
        usuario = Usuario.objects.create_user(
            username="factuser",
            email="fact@test.com",
            password="password123",
            nombres="Facturador",
            apellidos="Test",
            documento="444555666",
            tipo_documento="CC",
            rol="admin"
        )
        factura = Factura.objects.create(
            cliente=usuario,
            numero="FAC-001",
            subtotal=100000,
            iva=19000,
            total=119000,
            estado="pendiente"
        )
        self.assertEqual(factura.numero, "FAC-001")
        self.assertEqual(factura.total, 119000)
