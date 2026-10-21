"""Mixins de formularios estrictos.

- Rechaza campos desconocidos en el POST (equivalente a ``unknown fields`` en DRF).
- Recorta espacios y rechaza valores solo-espacios en campos obligatorios.
"""

from django import forms

# Campos que el navegador/Django agregan y no son datos de negocio.
CAMPOS_SISTEMA = {
    "csrfmiddlewaretoken",
    "accion",
    "action",
    "submit",
    "btn_submit",
    "guardar",
    "next",
    "TOTAL_FORMS",
    "INITIAL_FORMS",
    "MIN_NUM_FORMS",
    "MAX_NUM_FORMS",
    "id",
    "DELETE",
    "ORDER",
}


class StrictFormMixin:
    campos_extra_permitidos: set = set()

    def _campos_desconocidos(self):
        if not self.is_bound:
            return set()
        enviados = set(self.data.keys()) | set(getattr(self, "files", {}) or {})
        # Prefijos de formulario
        if self.prefix:
            enviados = {k.removeprefix(f"{self.prefix}-") for k in enviados}
        permitidos = set(self.fields) | CAMPOS_SISTEMA | set(self.campos_extra_permitidos)
        # Los ClearableFileInput envían "<campo>-clear"
        permitidos |= {f"{f}-clear" for f in self.fields}
        return enviados - permitidos

    def clean(self):
        cleaned = super().clean()
        desconocidos = self._campos_desconocidos()
        if desconocidos:
            raise forms.ValidationError(
                "Campos no permitidos en la solicitud: %(campos)s.",
                code="campos_desconocidos",
                params={"campos": ", ".join(sorted(desconocidos))},
            )
        return cleaned


class StrictForm(StrictFormMixin, forms.Form):
    pass


class StrictModelForm(StrictFormMixin, forms.ModelForm):
    pass
