import re

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.forms import inlineformset_factory

from config.forms import StrictModelForm
from config.validators import texto_sin_simbolos

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
    categoria = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        initial="General",
        validators=[texto_sin_simbolos],
    )

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
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre Legal",
                    "pattern": r"[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-#\/.,°]*",
                    "title": "Sin símbolos (solo letras, números y - # / . , )",
                    "oninput": r"this.value = this.value.replace(/[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-#\/.,°]/g, '')",
                }
            ),
            "nit": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "900000000-1",
                }
            ),
            "contacto_nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de contacto",
                    "pattern": r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]*",
                    "title": "Solo letras y espacios",
                    "oninput": r"this.value = this.value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]/g, '')",
                }
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
                attrs={
                    "class": "form-control",
                    "placeholder": "Calle, número, piso...",
                    "pattern": r"[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-#\/.,°]*",
                    "title": "Sin símbolos (solo letras, números y - # / . , )",
                    "oninput": r"this.value = this.value.replace(/[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ\s\-#\/.,°]/g, '')",
                }
            ),
            "ciudad": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ciudad",
                    "pattern": r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]*",
                    "title": "Solo letras y espacios",
                    "oninput": r"this.value = this.value.replace(/[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]/g, '')",
                }
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


class MaterialStockSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        material = getattr(value, "instance", None)
        if material is not None:
            stock = getattr(material, "stock", 0)
            try:
                stock = material.stock_info.cantidad_actual
            except ObjectDoesNotExist:
                pass
            option["attrs"]["data-stock"] = stock
        return option


class ProveedorMaterialForm(forms.ModelForm):
    cantidad_recibida = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=100000,
        label="Cantidad recibida",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "1",
                "max": "100000",
                "step": "1",
                "placeholder": "1",
            }
        ),
    )

    class Meta:
        model = ProveedorMaterial
        fields = ["material", "precio_actual", "referencia_proveedor", "observaciones", "activo"]
        widgets = {
            "material": MaterialStockSelect(attrs={"class": "form-control"}),
            "precio_actual": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "1000",
                    "inputmode": "decimal",
                    "placeholder": "0,00",
                    "title": "El precio debe ser mayor que cero.",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["material"].queryset = self.fields["material"].queryset.select_related(
            "stock_info"
        ).order_by("nombre")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("material") and not self.instance.pk and not cleaned.get("cantidad_recibida"):
            self.add_error("cantidad_recibida", "Indica cuántas unidades recibiste para agregar este material.")
        return cleaned


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
        self.fields["proveedor"].queryset = Proveedor.objects.filter(activo=True).order_by("nombre_empresa")


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
