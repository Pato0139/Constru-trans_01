from django import forms
from django.forms import inlineformset_factory

from usuarios.models import Proveedor

from .models import Compra, DetalleCompra, ProveedorMaterial


class ProveedorPerfilForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "nombre_empresa",
            "contacto_nombre",
            "nit",
            "telefono",
            "correo",
            "direccion",
            "ciudad",
            "activo",
            "categoria",
            "descripcion",
        ]


class ProveedorMaterialForm(forms.ModelForm):
    class Meta:
        model = ProveedorMaterial
        fields = ["material", "precio_actual", "referencia_proveedor", "observaciones", "activo"]


ProveedorMaterialFormSet = inlineformset_factory(
    Proveedor,
    ProveedorMaterial,
    form=ProveedorMaterialForm,
    extra=1,
    can_delete=True,
)


class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ["proveedor", "observaciones"]
        widgets = {
            "proveedor": forms.Select(attrs={"class": "form-control select2"}),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Notas adicionales..."}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proveedor"].queryset = Proveedor.objects.all()


class DetalleCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleCompra
        fields = ["material", "cantidad", "precio_unitario"]
        widgets = {
            "material": forms.Select(attrs={"class": "form-control select2 material-select"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control cantidad-input", "min": 1}),
            "precio_unitario": forms.NumberInput(
                attrs={"class": "form-control precio-input", "step": "0.01", "min": 0, "readonly": True}
            ),
        }


DetalleCompraFormSet = inlineformset_factory(
    Compra, DetalleCompra, form=DetalleCompraForm, extra=1, can_delete=True
)
