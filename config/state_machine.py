"""Máquina de estados mínima basada en un diccionario de transiciones.

Uso::

    class Pedido(TransicionMixin, models.Model):
        CAMPO_ESTADO = "estado"
        TRANSICIONES = {"pendiente": {"aprobado", "cancelado"}, ...}

    pedido.transicionar("aprobado")   # lanza ValidationError si no se permite
"""

from django.core.exceptions import ValidationError


class TransicionMixin:
    CAMPO_ESTADO = "estado"
    TRANSICIONES: dict = {}

    def puede_transicionar(self, nuevo):
        actual = getattr(self, self.CAMPO_ESTADO)
        if nuevo == actual:
            return True
        return nuevo in self.TRANSICIONES.get(actual, set())

    def transiciones_disponibles(self):
        actual = getattr(self, self.CAMPO_ESTADO)
        return sorted(self.TRANSICIONES.get(actual, set()))

    def transicionar(self, nuevo):
        field = self._meta.get_field(self.CAMPO_ESTADO)
        validos = {c[0] for c in field.choices or ()}
        if validos and nuevo not in validos:
            raise ValidationError(
                {self.CAMPO_ESTADO: "El estado seleccionado no es válido."},
                code="estado_invalido",
            )
        if not self.puede_transicionar(nuevo):
            actual = getattr(self, self.CAMPO_ESTADO)
            etiquetas = dict(field.choices or ())
            raise ValidationError(
                {
                    self.CAMPO_ESTADO: (
                        f"No se permite pasar de «{etiquetas.get(actual, actual)}» "
                        f"a «{etiquetas.get(nuevo, nuevo)}»."
                    )
                },
                code="transicion_invalida",
            )
        setattr(self, self.CAMPO_ESTADO, nuevo)
