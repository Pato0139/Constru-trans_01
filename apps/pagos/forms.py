from django import forms

from apps.pagos.models import Factura, PagoFactura
from apps.pedidos.models import Pago
from apps.pedidos.validators import validar_comprobante_imagen
from apps.pedidos.forms_pagos import PagoRevisionForm as _PagoRevisionBase
from config.forms_base import StrictModelForm

PagoRevisionForm = _PagoRevisionBase


class PagoRegistroForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["metodo", "comprobante"]
        widgets = {
            "metodo": forms.Select(attrs={"class": "form-select"}),
            "comprobante": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_comprobante(self):
        comprobante = self.cleaned_data.get("comprobante")
        if comprobante:
            validar_comprobante_imagen(comprobante)
        return comprobante

    def clean(self):
        cleaned = super().clean()
        metodo = cleaned.get("metodo")
        comprobante = cleaned.get("comprobante")
        if metodo in Pago.METODOS_CON_COMPROBANTE and not comprobante:
            self.add_error("comprobante", "Este método de pago requiere comprobante.")
        return cleaned


# PagoRevisionForm: se reexporta (arriba) la versión estricta de apps.pedidos.forms_pagos.


class PagoFacturaRegistroForm(StrictModelForm):
    class Meta:
        model = PagoFactura
        fields = ["monto", "metodo", "referencia", "evidencia"]
        error_messages = {
            "monto": {
                "required": "El monto es obligatorio.",
                "invalid": "El monto debe ser un número válido.",
                "max_digits": "El monto no puede tener más de %(max)s dígitos.",
                "max_decimal_places": "El monto admite máximo %(max)s decimales.",
            },
            "metodo": {"invalid_choice": "El método de pago seleccionado no es válido."},
            "referencia": {"max_length": "La referencia no puede superar %(limit_value)d caracteres."},
        }

    def __init__(self, *args, factura: Factura, **kwargs):
        self.factura = factura
        super().__init__(*args, **kwargs)

    def clean_monto(self):
        monto = self.cleaned_data["monto"]
        if not monto.is_finite():
            raise forms.ValidationError("El monto debe ser un número válido.")
        if monto <= 0 or monto > self.factura.saldo_pendiente:
            raise forms.ValidationError("El monto debe ser positivo y no superar el saldo pendiente.")
        return monto

    def clean_referencia(self):
        return (self.cleaned_data.get("referencia") or "").strip()


class PagoFacturaRevisionForm(PagoRevisionForm):
    # Contrato previo: el rechazo de un pago de factura no exigía motivo.
    motivo_obligatorio = False
