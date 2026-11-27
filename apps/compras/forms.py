import re

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.forms import formset_factory, inlineformset_factory
from django.utils import timezone

from apps.catalogo.models import MaterialConstruccion
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
            unidad = getattr(material, "unidad_medida", None)
            option["attrs"]["data-unit"] = (
                getattr(unidad, "abreviatura", None)
                or getattr(unidad, "nombre", None)
                or "unidades"
            )
            option["attrs"]["data-stock"] = stock
            option["attrs"]["data-precio"] = str(getattr(material, "precio_referencia", 0) or 0)
        return option


class ProveedorMaterialForm(forms.ModelForm):
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
            "stock_info", "unidad_medida"
        ).order_by("nombre")

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


class EntradaCompraForm(forms.ModelForm):
    clave_idempotencia = forms.UUIDField(widget=forms.HiddenInput())

    class Meta:
        model = Compra
        fields = ["proveedor", "fecha_compra", "numero_factura", "observaciones"]
        widgets = {
            "proveedor": forms.Select(attrs={"class": "form-select"}),
            "fecha_compra": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "numero_factura": forms.TextInput(attrs={"class": "form-control", "maxlength": 100}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_compra"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["proveedor"].queryset = Proveedor.objects.filter(activo=True).order_by("nombre_empresa")
        self.fields["fecha_compra"].initial = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        self.fields["numero_factura"].required = False
        self.fields["observaciones"].required = False


class EntradaDetalleCompraForm(forms.ModelForm):
    precio_venta_unitario = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control sale-price", "min": "0", "step": "0.01"}),
    )
    actualizar_precio_venta = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input update-sale-price"}),
    )

    class Meta:
        model = DetalleCompra
        fields = ["material", "cantidad", "precio_unitario"]
        widgets = {
            "material": MaterialStockSelect(attrs={"class": "form-select material-select"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control quantity-input", "min": 1, "step": 1}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control purchase-price", "min": "0.01", "step": "0.01"}),
        }

    def __init__(self, *args, proveedor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["material"].queryset = MaterialConstruccion.objects.filter(activo=True, proveedores_ofertantes__proveedor=proveedor, proveedores_ofertantes__activo=True).select_related(
            "stock_info", "unidad_medida"
        ).order_by("nombre")
        self.fields["precio_unitario"].min_value = 0.01
        self.fields["precio_unitario"].label = "Precio de compra unitario"
        self.fields["precio_venta_unitario"].label = "Precio de venta"
        self.fields["actualizar_precio_venta"].label = "Actualizar precio de venta del catálogo"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("actualizar_precio_venta") and not cleaned.get("precio_venta_unitario"):
            self.add_error("precio_venta_unitario", "Indica el precio de venta que deseas aplicar.")
        return cleaned


class BaseEntradaDetalleFormSet(forms.BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        materiales = [
            form.cleaned_data["material"]
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE") and form.cleaned_data.get("material")
        ]
        if not materiales:
            raise forms.ValidationError("Agrega al menos un material a la entrada.")
        if len(materiales) != len(set(m.pk for m in materiales)):
            raise forms.ValidationError("No repitas materiales; agrega una sola fila por material.")


EntradaDetalleCompraFormSet = formset_factory(
    EntradaDetalleCompraForm, formset=BaseEntradaDetalleFormSet, extra=0, can_delete=True, min_num=1, validate_min=True
)
