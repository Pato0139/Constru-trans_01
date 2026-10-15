from django import forms

from apps.pedidos.models import Pago


class PagoRegistroForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["metodo", "comprobante"]
        widgets = {
            "metodo": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "comprobante": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/png,image/jpeg"}
            ),
        }

    def clean_comprobante(self):
        comprobante = self.cleaned_data.get("comprobante")
        if comprobante:
            content_type = getattr(comprobante, "content_type", "")
            if content_type not in ("image/png", "image/jpeg"):
                raise forms.ValidationError("Solo se permiten archivos PNG o JPG.")
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
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Motivo o comentario de la revisión",
            }
        ),
    )
