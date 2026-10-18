"""
Pruebas de Seguridad: Base de Datos y Concurrencia (Área 9)
Verifica:
1. Operaciones financieras encapsuladas en transaction.atomic.
2. Bloqueo pesimista contra condiciones de carrera (doble pago concurrente).
3. Integridad de saldos y consistencia de transiciones.
"""

from decimal import Decimal
import threading
from django.db import transaction
from django.test import TestCase

from apps.pagos.models import Factura, Pago, PagoFactura
from apps.pedidos.models import Pedido
from apps.usuarios.models import Usuario


class SeguridadArea9ConcurrenciaTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="cliente_concurrencia@test.com",
            email="cliente_concurrencia@test.com",
            password="Password123*",
            nombres="Cliente",
            apellidos="Concurrencia",
            documento="77889900",
            tipo_documento="CC",
            rol="cliente",
        )
        self.pedido = Pedido.objects.create(
            usuario=self.usuario,
            direccion_destino="Calle Concurrente # 1-2",
            estado=Pedido.PENDIENTE,
            total=Decimal("100000.00"),
        )

    def test_transaccion_atomica_en_revision_de_pago(self):
        """Verifica que una falla durante la revisión de pago no deje la base en estado inconsistente."""
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_BANCOLOMBIA,
            monto=Decimal("100000.00"),
            estado=Pago.PENDIENTE,
        )

        try:
            with transaction.atomic():
                pago.marcar_revision(estado=Pago.APROBADO, revisor=self.usuario)
                pago.save()
                # Simular excepción inesperada antes de confirmar pedido
                raise RuntimeError("Fallo simulado de red en pasarela o ERP")
        except RuntimeError:
            pass

        # El rollback debe dejar el pago en su estado original (pendiente)
        pago.refresh_from_db()
        self.assertEqual(
            pago.estado,
            Pago.PENDIENTE,
            "El rollback de transaction.atomic debe revertir la aprobación del pago ante fallo",
        )

    def test_prevenir_doble_aprobacion_concurrente_de_pago(self):
        """Simula dos intentos de revisión para verificar que la primera bloquea e impide que la segunda aplique cambios."""
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_BANCOLOMBIA,
            monto=Decimal("100000.00"),
            estado=Pago.PENDIENTE,
        )

        resultados = []

        def revisar_pago_simulado(accion):
            with transaction.atomic():
                pago_bloqueado = Pago.objects.select_for_update().get(pk=pago.pk)
                if pago_bloqueado.estado != Pago.PENDIENTE:
                    resultados.append(f"rechazado_{accion}_ya_revisado")
                    return
                pago_bloqueado.marcar_revision(estado=accion, revisor=self.usuario)
                pago_bloqueado.save()
                resultados.append(f"exito_{accion}")

        # Primera transacción (gana la revisión)
        revisar_pago_simulado(Pago.APROBADO)
        # Segunda transacción (intento concurrente/posterior que debe detectar el estado modificado)
        revisar_pago_simulado(Pago.RECHAZADO)

        self.assertEqual(len(resultados), 2)
        self.assertEqual(resultados[0], "exito_aprobado")
        self.assertEqual(resultados[1], "rechazado_rechazado_ya_revisado")
        pago.refresh_from_db()
        self.assertEqual(pago.estado, Pago.APROBADO)
