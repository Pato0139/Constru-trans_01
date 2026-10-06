from django import forms
from .models import SugerenciaRecomendacion


class SugerenciaForm(forms.ModelForm):
    class Meta:
        model = SugerenciaRecomendacion
        fields = ["tipo", "titulo", "descripcion"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-control"}),
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }
