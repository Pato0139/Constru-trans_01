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
    q = forms.CharField(required=False, max_length=100, strip=True)
    fecha = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        error_messages={"invalid": "La fecha debe tener el formato AAAA-MM-DD."},
    )
    estado = forms.ChoiceField(
        required=False,
        choices=[("", "")] + list(Pedido.ESTADOS),
        error_messages={"invalid_choice": "El estado del filtro no es válido."},
    )
