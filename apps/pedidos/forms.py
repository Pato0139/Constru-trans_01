from django import forms

from config.forms_base import StrictForm
from config.validators import CANTIDAD_MAXIMA

from .models import Pedido


class CambioEstadoPedidoForm(StrictForm):
    """POST del admin en ver_pedido_admin. El backend decide si la transición es válida."""

    estado = forms.ChoiceField(
        choices=Pedido.ESTADOS,
        error_messages={
            "required": "Selecciona un estado.",
            "invalid_choice": "El estado seleccionado no es válido.",
        },
    )
    observacion = forms.CharField(required=False, max_length=2000, strip=True)

    def __init__(self, *args, pedido=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pedido = pedido

    def clean(self):
        cleaned_data = super().clean()
        if self.pedido:
            if self.pedido.estado in (Pedido.ENTREGADO, Pedido.CANCELADO):
                raise forms.ValidationError(
                    "El pedido se encuentra en un estado final y no puede ser modificado."
                )
            transporte_asignado = bool(
                (self.pedido.envio_actual and self.pedido.envio_actual.conductor_id and self.pedido.envio_actual.vehiculo_id)
                or (self.pedido.conductor_id and self.pedido.vehiculo_asignado_actual)
                or self.pedido.estado in (Pedido.VEHICULO_ASIGNADO, Pedido.EN_RUTA)
            )
            if transporte_asignado or self.pedido.estado in (Pedido.VEHICULO_ASIGNADO, Pedido.EN_RUTA):
                raise forms.ValidationError(
                    "El pedido ya tiene conductor y vehículo asignados o está en ruta; su estado no se puede modificar desde el Control Maestro."
                )
            nuevo_estado = cleaned_data.get("estado")
            if nuevo_estado == Pedido.VEHICULO_ASIGNADO:
                raise forms.ValidationError(
                    "No se puede asignar el estado «Vehículo Asignado» directamente sin asignar un conductor y vehículo válidos."
                )
        return cleaned_data


class AgregarMaterialForm(StrictForm):
    material = forms.IntegerField(
        min_value=1,
        error_messages={"required": "Selecciona un material.", "invalid": "Material inválido."},
    )
    cantidad = forms.IntegerField(
        min_value=1,
        max_value=CANTIDAD_MAXIMA,
        error_messages={
            "required": "La cantidad es obligatoria.",
            "invalid": "La cantidad debe ser un entero.",
            "min_value": "La cantidad mínima es 1.",
            "max_value": f"La cantidad no puede superar {CANTIDAD_MAXIMA}.",
        },
    )


class FiltroPedidosForm(forms.Form):
    """Valida el query string de las listas (no estricto: GET puede traer page, etc.)."""

    cliente = forms.CharField(required=False, max_length=100, strip=True)
    destino = forms.CharField(required=False, max_length=150, strip=True)
    q = forms.CharField(required=False, max_length=100, strip=True)
    fecha = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        error_messages={"invalid": "La fecha debe tener el formato AAAA-MM-DD."},
    )
    estado = forms.ChoiceField(
        required=False,
        choices=[("", "")]
        + list(Pedido.ESTADOS)
        + [("pendiente_correccion_pago", "Pendiente de corrección de pago")],
        error_messages={"invalid_choice": "El estado del filtro no es válido."},
    )
