from django.test import TestCase
from usuarios.models import Usuario, MetodoPago
from facturacion.models import Factura
from pagos.models import Pago


class PagoModelTests(TestCase):
    def test_crear_pago(self):
        """Prueba crear un pago asociado a una factura"""
        usuario = Usuario.objects.create_user(
            username="pagouser",
            email="pago@test.com",
            password="password123",
            nombres="Pagos",
            apellidos="Test",
            documento="777888999",
            tipo_documento="CC",
            rol="admin"
        )
        factura = Factura.objects.create(
            cliente=usuario,
            subtotal=100000,
            iva=19000,
            total=119000,
            estado="pendiente"
        )
        metodo_pago = MetodoPago.objects.create(
            codigo_metodo_pago="EFECT",
            metodo="Efectivo"
        )
        pago = Pago.objects.create(
            factura=factura,
            monto=50000,
            codigo_metodo_pago=metodo_pago,
            registrado_por=usuario
        )
        self.assertEqual(pago.factura, factura)
        self.assertEqual(pago.monto, 50000)

    def test_pago_marca_factura_como_pagada(self):
        usuario = Usuario.objects.create_user(
            username="pagouser2",
            email="pago2@test.com",
            password="password123",
            nombres="Pagos",
            apellidos="Test",
            documento="111999000",
            tipo_documento="CC",
            rol="admin",
        )
        factura = Factura.objects.create(
            cliente=usuario,
            subtotal=100000,
            iva=19000,
            total=119000,
            estado="pendiente",
        )
        metodo_pago = MetodoPago.objects.create(
            codigo_metodo_pago="TRANSF",
            metodo="Transferencia",
        )
        Pago.objects.create(
            factura=factura,
            monto=119000,
            codigo_metodo_pago=metodo_pago,
            registrado_por=usuario,
        )
        factura.refresh_from_db()
        self.assertEqual(factura.estado, "pagada")
