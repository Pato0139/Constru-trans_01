from django import forms
from django.forms import inlineformset_factory

from config.forms import StrictModelForm
from .models import Compra, DetalleCompra, Proveedor, ProveedorMaterial


class ProveedorForm(StrictModelForm):
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
            "categoria",
            "descripcion",
            "activo",
        ]
        widgets = {
            "nombre_empresa": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombre Legal"}
            ),
            "nit": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "900000000-1",
                }
            ),
            "contacto_nombre": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombre de contacto"}
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "3001234567",
                }
            ),
            "correo": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "empresa@correo.com"}
            ),
            "direccion": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Calle, número, piso..."}
            ),
            "ciudad": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ciudad"}
            ),
            "categoria": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Materiales, Repuestos, Tecnología...",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Descripción..."}
            ),
            "activo": forms.CheckboxInput(
                attrs={"class": "form-check-input mt-2"}
            ),
        }

    def clean_nit(self):
        nit = self.cleaned_data.get("nit")
        return nit.strip() if nit else ""

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        return telefono.strip() if telefono else ""


class ProveedorPerfilForm(StrictModelForm):
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


class ProveedorMaterialForm(StrictModelForm):
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


class CompraForm(StrictModelForm):
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


class DetalleCompraForm(StrictModelForm):
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
