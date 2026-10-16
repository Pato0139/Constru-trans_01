from django.test import SimpleTestCase

from apps.clientes.views import _normalizar_items_pedido


class NormalizarItemsPedidoTests(SimpleTestCase):
    def test_acepta_items_validos(self):
        items, error = _normalizar_items_pedido(["12", "24"], ["2", "5"])

        self.assertEqual(items, [(12, 2), (24, 5)])
        self.assertIsNone(error)

    def test_rechaza_cantidades_no_positivas_o_excesivas(self):
        for cantidad in ("0", "-1", "100001", "invalida"):
            with self.subTest(cantidad=cantidad):
                items, error = _normalizar_items_pedido(["12"], [cantidad])

                self.assertIsNone(items)
                self.assertIsNotNone(error)

    def test_rechaza_ids_repetidos_y_listas_desalineadas(self):
        for ids, cantidades in ((["12", "12"], ["1", "2"]), (["12"], ["1", "2"])):
            with self.subTest(ids=ids, cantidades=cantidades):
                items, error = _normalizar_items_pedido(ids, cantidades)

                self.assertIsNone(items)
                self.assertIsNotNone(error)

    def test_rechaza_mas_de_cincuenta_lineas(self):
        items, error = _normalizar_items_pedido(
            [str(item) for item in range(51)],
            ["1"] * 51,
        )

        self.assertIsNone(items)
        self.assertIsNotNone(error)
