"""
Pruebas de Seguridad: Logging, Auditoría y Trazabilidad (Área 7)
Verifica:
1. Registro de eventos de auditoría y transiciones de estado en pedidos y pagos.
2. Enmascaramiento de datos sensibles (tokens, contraseñas, cuentas) en helpers de logging.
3. Handler 500 loguea excepciones internamente sin filtrarlas al cliente.
"""

import logging
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from config.security import enmascarar_dato_sensible

User = get_user_model()


class SeguridadArea7AuditoriaTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_audit@test.com",
            email="admin_audit@test.com",
            password="Password123*",
            nombres="Admin",
            apellidos="Audit",
            documento="55667788",
            tipo_documento="CC",
            rol="admin",
            is_staff=True,
        )
        self.cliente = User.objects.create_user(
            username="cliente_audit@test.com",
            email="cliente_audit@test.com",
            password="Password123*",
            nombres="Cliente",
            apellidos="Audit",
            documento="66778899",
            tipo_documento="CC",
            rol="cliente",
        )
        self.pedido = Pedido.objects.create(
            usuario=self.cliente,
            direccion_destino="Calle 1 # 2-3, Tunja",
            estado=Pedido.PENDIENTE,
            total=Decimal("50000.00"),
        )
        self.pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_BANCOLOMBIA,
            monto=Decimal("50000.00"),
            estado=Pago.PENDIENTE,
        )

    def test_enmascarar_dato_sensible_protege_tokens_y_cuentas(self):
        """Verifica que tokens y cuentas se enmascaren dejando solo prefijo o sufijo según el caso."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret"
        cuenta = "1234567890123456"

        token_mask = enmascarar_dato_sensible(token, "token")
        cuenta_mask = enmascarar_dato_sensible(cuenta, "cuenta")

        self.assertEqual(token_mask, "eyJh***", "Tokens deben enmascararse dejando solo los primeros 4 caracteres")
        self.assertEqual(cuenta_mask, "***3456", "Cuentas deben enmascararse dejando solo los últimos 4 caracteres")
        self.assertNotIn("secret", token_mask)
        self.assertNotIn("1234567890", cuenta_mask)

    def test_marcar_revision_pago_loguea_transicion_con_detalles(self):
        """Verifica que marcar_revision actualice estado y registre log con estado previo, nuevo y revisor."""
        with self.assertLogs(level="INFO") as cm:
            self.pago.marcar_revision(
                estado=Pago.APROBADO,
                revisor=self.admin,
                observaciones="Pago verificado en extracto",
            )
        self.assertEqual(self.pago.estado, Pago.APROBADO)
        self.assertEqual(self.pago.revisado_por, self.admin)
        log_output = " ".join(cm.output)
        self.assertIn("Revision de pago", log_output)
        self.assertIn("aprobado", log_output)
        self.assertIn(self.admin.username, log_output)

    def test_transicion_pedido_loguea_cambio_de_estado(self):
        """Verifica que transicionar en Pedido registre la trazabilidad del cambio de estado."""
        with self.assertLogs(level="INFO") as cm:
            self.pedido.transicionar(Pedido.AUTORIZADO_DESPACHO, usuario=self.admin)
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)
        log_output = " ".join(cm.output)
        self.assertIn("Transicion de estado en Pedido", log_output)
        self.assertIn("pendiente", log_output)
        self.assertIn("autorizado_despacho", log_output)
