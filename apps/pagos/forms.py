from django import forms

from .models import Pago


class PagoRegistroForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["metodo", "monto", "comprobante"]
        widgets = {
            "metodo": forms.Select(attrs={"class": "form-select"}),
            "monto": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "comprobante": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

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
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Motivo o comentario de la revisión",
            }
        ),
    )
