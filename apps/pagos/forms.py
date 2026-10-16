from django import forms

from apps.pagos.models import Factura, PagoFactura
from apps.pedidos.models import Pago
from apps.pagos.models import Pago
from apps.pedidos.validators import validar_comprobante_imagen


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


class PagoRevisionForm(forms.Form):
    observaciones = forms.CharField(
        required=False,
        max_length=1000,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Motivo o comentario de la revisión",
            }
        ),
    )


class PagoFacturaRegistroForm(forms.ModelForm):
    class Meta:
        model = PagoFactura
        fields = ["monto", "metodo", "referencia", "evidencia"]

    def __init__(self, *args, factura: Factura, **kwargs):
        self.factura = factura
        super().__init__(*args, **kwargs)

    def clean_monto(self):
        monto = self.cleaned_data["monto"]
        if monto <= 0 or monto > self.factura.saldo_pendiente:
            raise forms.ValidationError("El monto debe ser positivo y no superar el saldo pendiente.")
        return monto

    def clean_referencia(self):
        return self.cleaned_data.get("referencia", "").strip()

    def clean_evidencia(self):
        evidencia = self.cleaned_data.get("evidencia")
        if evidencia and evidencia.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La evidencia no puede superar los 5 MB.")
        return evidencia
