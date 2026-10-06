import re
import unicodedata

from django import forms
from django.db.models import Q

from .models import Catalogo, Marca, MaterialConstruccion, Stock, UnidadMedida


class MaterialForm(forms.ModelForm):
    _MARCA_PALABRAS_PROHIBIDAS = {
        "cabron",
        "cojones",
        "cono",
        "estupido",
        "gonorrea",
        "hijueputa",
        "imbecil",
        "joder",
        "marica",
        "mierda",
        "pendejo",
        "puta",
        "puto",
        "verga",
    }

    tipo = forms.ModelChoiceField(
        queryset=Catalogo.objects.all().order_by("nombre_empresa"),
        required=False,
        label="Tipo de Material",
        empty_label="-- Seleccione un tipo --",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )
    marca_nombre = forms.CharField(
        required=False,
        label="Marca",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ej: Argos",
            }
        ),
    )
    stock = forms.IntegerField(
        required=False,
        min_value=0,
        label="Stock actual",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control numeric-only",
                "placeholder": "0",
            }
        ),
    )
    ubicacion = forms.CharField(
        required=False,
        label="Ubicación en bodega",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ej: Almacén 1",
            }
        ),
    )

    class Meta:
        model = MaterialConstruccion
        fields = ["nombre", "unidad_medida", "descripcion", "precio_referencia"]
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Cemento Gris",
                }
            ),
            "unidad_medida": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Descripción detallada...",
                }
            ),
            "precio_referencia": forms.TextInput(
                attrs={
                    "class": "form-control decimal-only",
                    "inputmode": "decimal",
                    "placeholder": "0.00",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["unidad_medida"].queryset = UnidadMedida.objects.filter(activa=True).order_by(
            "orden", "nombre"
        )
        self.fields["unidad_medida"].empty_label = "-- Seleccione una unidad --"

        if self.instance and self.instance.pk and self.instance.catalogo:
            self.fields["tipo"].initial = self.instance.catalogo
        if self.instance and self.instance.pk and self.instance.marca:
            self.fields["marca_nombre"].initial = self.instance.marca.nombre
        if self.instance and self.instance.pk:
            try:
                stock = self.instance.stock_info
                self.fields["stock"].initial = stock.cantidad_actual
                self.fields["ubicacion"].initial = stock.ubicacion
            except Stock.DoesNotExist:
                self.fields["stock"].initial = 0

    def clean_marca_nombre(self):
        marca_nombre = self.cleaned_data.get("marca_nombre", "").strip()
        if not marca_nombre:
            return "N/A"

        normalizado = unicodedata.normalize("NFKD", marca_nombre)
        normalizado = "".join(
            caracter for caracter in normalizado if not unicodedata.combining(caracter)
        ).lower()
        palabras = set(re.findall(r"[a-z0-9]+", normalizado))
        frases_prohibidas = {"hijo de puta", "la concha de tu madre"}

        if palabras & self._MARCA_PALABRAS_PROHIBIDAS or any(
            frase in normalizado for frase in frases_prohibidas
        ):
            raise forms.ValidationError("El nombre de la marca contiene lenguaje no permitido.")

        return marca_nombre

    def save(self, commit=True):
        material = super().save(commit=False)
        tipo = self.cleaned_data.get("tipo")
        material.catalogo = tipo

        marca_nombre = self.cleaned_data["marca_nombre"]
        marca = Marca.objects.filter(nombre__iexact=marca_nombre).first()
        material.marca = marca or Marca.objects.create(nombre=marca_nombre)

        if commit:
            material.save()

        stock_value = self.cleaned_data.get("stock")
        ubicacion = self.cleaned_data.get("ubicacion", "")

        if stock_value is not None:
            stock_obj, created = Stock.objects.get_or_create(
                material=material,
                defaults={
                    "cantidad_actual": stock_value,
                    "ubicacion": ubicacion or "",
                },
            )
            if not created:
                stock_obj.cantidad_actual = stock_value
                stock_obj.ubicacion = ubicacion or stock_obj.ubicacion
                stock_obj.save()

        return material


class UnidadMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadMedida
        fields = ["codigo", "nombre", "abreviatura", "activa"]
        labels = {
            "codigo": "Código de Unidad",
            "nombre": "Nombre de la Unidad",
            "abreviatura": "Abreviatura",
            "activa": "Activa",
        }
        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: M3",
                    "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Metro cúbico",
                    "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
                }
            ),
            "abreviatura": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: m³",
                    "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
                }
            ),
            "activa": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def clean_codigo(self):
        codigo = self.cleaned_data.get("codigo")
        if codigo:
            codigo = codigo.strip().upper()
            if not self.instance.pk and UnidadMedida.objects.filter(codigo=codigo).exists():
                raise forms.ValidationError("Ya existe una unidad con este código.")
        return codigo

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre")
        if nombre:
            return nombre.strip()
        return nombre


class CatalogoForm(forms.ModelForm):
    class Meta:
        model = Catalogo
        fields = ["codigo_catalogo", "nombre_empresa"]
        labels = {
            "codigo_catalogo": "Código Único del Tipo",
            "nombre_empresa": "Nombre del Tipo de Material",
        }
        widgets = {
            "codigo_catalogo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: TIPO-CEM",
                    "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
                }
            ),
            "nombre_empresa": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej: Cementos y Hormigón",
                    "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
                }
            ),
        }

    def clean_codigo_catalogo(self):
        codigo = self.cleaned_data.get("codigo_catalogo")
        if codigo:
            codigo = codigo.strip().upper()

            if not self.instance.pk and Catalogo.objects.filter(codigo_catalogo=codigo).exists():
                raise forms.ValidationError("Ya existe un tipo de material con este código.")
        return codigo
