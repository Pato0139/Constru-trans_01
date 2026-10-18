from django import forms

from config.forms_base import StrictModelForm
from config.validators import no_solo_espacios
from .models import SugerenciaRecomendacion


class SugerenciaForm(StrictModelForm):
    class Meta:
        model = SugerenciaRecomendacion
        fields = ["tipo", "titulo", "descripcion"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-control"}),
            "titulo": forms.TextInput(attrs={"class": "form-control", "maxlength": "200"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def clean_titulo(self):
        titulo = (self.cleaned_data.get("titulo") or "").strip()
        no_solo_espacios(titulo)
        return titulo

    def clean_descripcion(self):
        desc = (self.cleaned_data.get("descripcion") or "").strip()
        no_solo_espacios(desc)
        return desc
