import re

from django import forms
from django.forms import inlineformset_factory

from config.forms import StrictModelForm
from .models import Compra, DetalleCompra, Proveedor, ProveedorMaterial


class _ProveedorBaseForm(StrictModelForm):
    campos_extra_permitidos = {"email"}

    def clean_nombre_empresa(self):
        nombre = self.cleaned_data.get("nombre_empresa", "")
        return nombre.strip() if nombre else ""

    def clean_nit(self):
        nit = self.cleaned_data.get("nit", "")
        if nit:
            nit = str(nit).strip()
            # Quitar prefijos comunes como "NIT:", "NIT", "RUT", "CC"
            nit = re.sub(r"^(NIT|RUT|CC|CE)[:\s.\-]*", "", nit, flags=re.IGNORECASE)
            # Normalizar eliminando puntos y espacios comunes en formatos colombianos
            nit = re.sub(r"[.\s]", "", nit)
            nit = re.sub(r"-+", "-", nit)
            if nit.endswith("-"):
                nit = nit[:-1]
        return nit

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono", "")
        if telefono:
            telefono = str(telefono).strip()
            # Quitar prefijos comunes como "Tel:", "Cel:"
            telefono = re.sub(r"^(TEL|CEL|CELULAR|TELEFONO)[:\s.\-]*", "", telefono, flags=re.IGNORECASE)
            if telefono.startswith("+"):
                telefono = "+" + re.sub(r"\D", "", telefono)
            else:
                telefono = re.sub(r"\D", "", telefono)
        return telefono

    def clean_correo(self):
        correo = self.cleaned_data.get("correo", "")
        return correo.strip().lower() if correo else ""

    def clean_contacto_nombre(self):
        v = self.cleaned_data.get("contacto_nombre", "")
        return v.strip() if v else ""

    def clean_direccion(self):
        v = self.cleaned_data.get("direccion", "")
        return v.strip() if v else ""

    def clean_ciudad(self):
        v = self.cleaned_data.get("ciudad", "")
        return v.strip() if v else ""

    def clean_categoria(self):
        v = self.cleaned_data.get("categoria", "")
        return v.strip() if v else "General"

    def clean_descripcion(self):
        v = self.cleaned_data.get("descripcion", "")
        return v.strip() if v else ""


class ProveedorForm(_ProveedorBaseForm):
    categoria = forms.CharField(required=False, widget=forms.HiddenInput(), initial="General")

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


class ProveedorPerfilForm(_ProveedorBaseForm):
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
                attrs={
                    "class": "form-control precio-input",
                    "step": "0.01",
                    "min": 0,
                    "readonly": True,
                }
            ),
        }


DetalleCompraFormSet = inlineformset_factory(
    Compra, DetalleCompra, form=DetalleCompraForm, extra=1, can_delete=True
)
