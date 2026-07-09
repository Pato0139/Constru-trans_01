from django.test import SimpleTestCase

from pagos.services import registrar_estado_pago


class PaymentTransitionTests(SimpleTestCase):
    def test_approve_payment_changes_order_to_authorized(self):
        payment = type("Payment", (), {"estado_pago": "pendiente"})()
        order = type("Order", (), {"estado": "pendiente"})()

        registrar_estado_pago(payment, order, "pago aprobado")

        self.assertEqual(payment.estado_pago, "pago aprobado")
        self.assertEqual(order.estado, "autorizado_despacho")

    def test_reject_payment_requires_reason(self):
        payment = type("Payment", (), {"estado_pago": "pendiente"})()
        order = type("Order", (), {"estado": "pendiente"})()

        result = registrar_estado_pago(payment, order, "pago rechazado", motivo_rechazo="Comprobante ilegible")

        self.assertTrue(result)
        self.assertEqual(payment.estado_pago, "pago rechazado")
        self.assertEqual(order.estado, "pendiente")
