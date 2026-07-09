from django.test import SimpleTestCase

from pagos.prototype import (
    append_history_entry,
    calculate_order_totals,
    generate_order_code,
    update_payment_and_order_status,
)


class PrototypeFlowTests(SimpleTestCase):
    def test_calculate_order_totals(self):
        items = [
            {"name": "Cemento", "quantity": 5, "unit_price": 50000},
            {"name": "Arena", "quantity": 2, "unit_price": 120000},
        ]

        totals = calculate_order_totals(items)

        self.assertEqual(totals["subtotal"], 490000)
        self.assertEqual(totals["iva"], 93100)
        self.assertEqual(totals["total"], 583100)

    def test_generate_order_code_uses_next_sequence(self):
        orders = [{"id": "PED-000154"}]

        self.assertEqual(generate_order_code(orders), "PED-000155")

    def test_append_history_entry_adds_event(self):
        order = {"history": []}

        append_history_entry(order, "Método de pago seleccionado.")

        self.assertEqual(order["history"][0]["text"], "Método de pago seleccionado.")

    def test_accept_payment_sets_order_and_payment_status(self):
        order = {
            "payment_status": "Pendiente",
            "order_status": "Pendiente de pago",
            "history": [],
        }

        update_payment_and_order_status(order, "Pago aprobado")

        self.assertEqual(order["payment_status"], "Pago aprobado")
        self.assertEqual(order["order_status"], "Autorizado para despacho")
