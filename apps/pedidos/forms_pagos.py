from django import forms

from apps.pagos.models import Pago
from apps.pedidos.validators import validar_comprobante_imagen
from config.forms_base import StrictForm


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
            # No se confia en content_type: lo envia el cliente y se puede falsear.
            validar_comprobante_imagen(comprobante)
        return comprobante

    def clean(self):
        cleaned = super().clean()
        metodo = cleaned.get("metodo")
        comprobante = cleaned.get("comprobante")
        if metodo in Pago.METODOS_CON_COMPROBANTE and not comprobante:
            self.add_error("comprobante", "Este método de pago requiere comprobante.")
        return cleaned


class PagoRevisionForm(StrictForm):
    ACCIONES = (("aprobar", "Aprobar"), ("rechazar", "Rechazar"))
    motivo_obligatorio = True

    accion = forms.ChoiceField(
        choices=ACCIONES,
        required=False,  # el GET inicial no la envía; se exige en clean() si hay POST
        error_messages={"invalid_choice": "La acción seleccionada no es válida."},
    )
    observaciones = forms.CharField(
        required=False,
        max_length=1000,
        strip=True,
        error_messages={"max_length": "Las observaciones no pueden superar %(limit_value)d caracteres."},
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Motivo o comentario de la revisión",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        accion = cleaned.get("accion")
        if self.is_bound and not accion and "accion" not in self.errors:
            self.add_error("accion", "Debes indicar si apruebas o rechazas el pago.")
        if self.motivo_obligatorio and accion == "rechazar" and not cleaned.get("observaciones"):
            self.add_error("observaciones", "Indica el motivo del rechazo.")
        return cleaned
