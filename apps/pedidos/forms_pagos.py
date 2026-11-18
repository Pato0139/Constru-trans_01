from django import forms

from apps.pagos.models import Pago
from apps.pedidos.validators import validar_comprobante_imagen
from config.forms_base import StrictForm


class PagoComprobanteInput(forms.ClearableFileInput):
    template_name = "pagos/widgets/custom_clearable_file_input.html"


class PagoRegistroForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["metodo", "comprobante"]
        widgets = {
            "metodo": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "comprobante": PagoComprobanteInput(
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
    TIPOS_RECHAZO = (
        ("", "General / Otro motivo"),
        ("otro_motivo", "General / Otro motivo"),
        ("comprobante_invalido", "Comprobante inválido o ilegible"),
        ("sin_comprobante", "Ausencia de documentación / Sin comprobante"),
        ("datos_incorrectos", "Datos o importe inconsistentes"),
    )
    motivo_obligatorio = True

    accion = forms.ChoiceField(
        choices=ACCIONES,
        required=False,  # el GET inicial no la envía; se exige en clean() si hay POST
        error_messages={"invalid_choice": "La acción seleccionada no es válida."},
    )
    tipo_rechazo = forms.ChoiceField(
        choices=TIPOS_RECHAZO,
        required=False,
        error_messages={"invalid_choice": "El tipo de rechazo seleccionado no es válido."},
        widget=forms.Select(attrs={"class": "form-select bg-surface text-white"}),
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
