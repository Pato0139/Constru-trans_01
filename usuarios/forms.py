from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.db.models import Q

User = get_user_model()

from .models import (
    Catalogo,
    ConductorVehiculo,
    MaterialConstruccion,
    Proveedor,
    Stock,
    UnidadMedida,
    Usuario,
    Vehiculo,
)
from .utils import limpiar_telefono


class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = [
            "nombres",
            "apellidos",
            "telefono",
            "documento",
            "tipo_documento",
            "rol",
            "estado",
            "foto_perfil",
        ]
        widgets = {
            "rol": forms.Select(attrs={"class": "form-select"}),
            "tipo_documento": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_documento(self):
        documento = self.cleaned_data.get("documento")
        documento = limpiar_telefono(documento)
        if not (7 <= len(documento) <= 15):
            raise forms.ValidationError("El número de documento debe tener entre 7 y 15 dígitos.")

        existing = Usuario.objects.filter(documento=documento)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Este documento ya está registrado.")
        return documento

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        telefono = limpiar_telefono(telefono)
        if not (9 <= len(telefono) <= 15):
            raise forms.ValidationError("El número de teléfono debe tener entre 9 y 15 dígitos.")
        return telefono


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Usuario o Correo",
        widget=forms.TextInput(attrs={"class": "input-custom", "placeholder": "Usuario o Correo"}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={"class": "input-custom", "placeholder": "Contraseña", "id": "password"}
        ),
    )
    remember_me = forms.BooleanField(
        label="Recuérdame en este dispositivo", required=False, initial=False
    )
    captcha = forms.BooleanField(
        label="No soy un robot",
        required=True,
        error_messages={"required": "Por favor confirme que no es un robot."},
    )


class RegistroForm(forms.ModelForm):
    correo = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "input-custom", "placeholder": "ejemplo@correo.com"}
        )
    )
    contrasena = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "input-custom", "placeholder": "••••••••", "id": "id_contrasena"}
        )
    )
    confirmar_contrasena = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "input-custom",
                "placeholder": "••••••••",
                "id": "id_confirmar_contrasena",
            }
        ),
    )

    class Meta:
        model = Usuario
        fields = ["nombres", "apellidos", "tipo_documento", "documento", "telefono"]
        widgets = {
            "nombres": forms.TextInput(attrs={"class": "input-custom", "placeholder": "Juan"}),
            "apellidos": forms.TextInput(attrs={"class": "input-custom", "placeholder": "Pérez"}),
            "tipo_documento": forms.Select(attrs={"class": "input-custom form-select"}),
            "documento": forms.TextInput(
                attrs={
                    "class": "input-custom",
                    "placeholder": "12345678",
                    "pattern": "[0-9\\s]*",
                    "title": "Solo se admiten números y espacios",
                    "oninput": "this.value = this.value.replace(/[^0-9\\s]/g, '')",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "input-custom",
                    "placeholder": "3001234567",
                    "pattern": "[0-9\\s]*",
                    "title": "Solo se admiten números y espacios",
                    "oninput": "this.value = this.value.replace(/[^0-9\\s]/g, '')",
                }
            ),
        }

    def clean_correo(self):
        correo = self.cleaned_data.get("correo")
        if User.objects.filter(email=correo).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return correo

    def clean_contrasena(self):
        contrasena = self.cleaned_data.get("contrasena")
        if " " in contrasena:
            raise forms.ValidationError("La contraseña no puede contener espacios.")
        return contrasena

    def clean_documento(self):
        documento = self.cleaned_data.get("documento")
        documento = limpiar_telefono(documento)
        if not (7 <= len(documento) <= 15):
            raise forms.ValidationError("El número de documento debe tener entre 7 y 15 dígitos.")
        if Usuario.objects.filter(documento=documento).exists():
            raise forms.ValidationError("Este documento ya está registrado.")
        return documento

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        telefono = limpiar_telefono(telefono)
        if not (9 <= len(telefono) <= 15):
            raise forms.ValidationError("El número de teléfono debe tener entre 9 y 15 dígitos.")
        return telefono

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("contrasena")
        confirm_password = cleaned_data.get("confirmar_contrasena")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirmar_contrasena", "Las contraseñas no coinciden.")
        return cleaned_data


class AsignarVehiculoForm(forms.Form):
    vehiculo = forms.ModelChoiceField(
        queryset=Vehiculo.objects.none(),
        label="Vehículo",
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, conductor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if conductor is None:
            self.fields["vehiculo"].queryset = Vehiculo.objects.none()
            return

        vehiculo_actual = conductor.vehiculo_actual

        asignados_activos = ConductorVehiculo.objects.filter(fecha_fin__isnull=True).values_list(
            "vehiculo_id", flat=True
        )

        if vehiculo_actual is not None:
            disponibles = Vehiculo.objects.filter(
                Q(id_vehiculo=vehiculo_actual.id_vehiculo)
                | (Q(estado="disponible") & ~Q(id_vehiculo__in=asignados_activos))
            ).distinct()
        else:
            disponibles = Vehiculo.objects.filter(estado="disponible").exclude(
                id_vehiculo__in=asignados_activos
            )

        self.fields["vehiculo"].queryset = disponibles.order_by("placa")


class MaterialForm(forms.ModelForm):
    tipo = forms.ModelChoiceField(
        queryset=Catalogo.objects.all().order_by("nombre_empresa"),
        required=False,
        label="Tipo de Material",
        empty_label="-- Seleccione un tipo --",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
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
                "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
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
                "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
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
                    "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
                }
            ),
            "unidad_medida": forms.Select(
                attrs={
                    "class": "form-select",
                    "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Descripción detallada...",
                    "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
                }
            ),
            "precio_referencia": forms.TextInput(
                attrs={
                    "class": "form-control decimal-only",
                    "inputmode": "decimal",
                    "placeholder": "0.00",
                    "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["unidad_medida"].queryset = UnidadMedida.objects.using("remota").filter(activa=True).order_by(
            "orden", "nombre"
        )
        self.fields["unidad_medida"].empty_label = "-- Seleccione una unidad --"

        if self.instance and self.instance.pk and self.instance.catalogo:
            self.fields["tipo"].initial = self.instance.catalogo
        if self.instance and self.instance.pk:
            try:
                stock = self.instance.stock_info
                self.fields["stock"].initial = stock.cantidad_actual
                self.fields["ubicacion"].initial = stock.ubicacion
            except Stock.DoesNotExist:
                self.fields["stock"].initial = 0

    def save(self, commit=True):
        material = super().save(commit=False)
        tipo = self.cleaned_data.get("tipo")
        material.catalogo = tipo

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
        fields = ["codigo", "nombre", "abreviatura", "descripcion", "activa", "orden"]
        labels = {
            "codigo": "Código de Unidad",
            "nombre": "Nombre de la Unidad",
            "abreviatura": "Abreviatura",
            "descripcion": "Descripción",
            "activa": "Activa",
            "orden": "Orden",
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
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Descripción de la unidad...",
                    "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
                }
            ),
            "activa": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "orden": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0",
                    "style": "background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;",
                }
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


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["nombre_empresa", "nit", "telefono", "correo", "descripcion"]
        widgets = {
            "nombre_empresa": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombre Legal"}
            ),
            "nit": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "9000000000",
                    "pattern": "[0-9\\s]*",
                    "title": "Solo se admiten números y espacios",
                    "oninput": "this.value = this.value.replace(/[^0-9\\s]/g, '')",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "3001234567",
                    "pattern": "[0-9\\s]*",
                    "title": "Solo se admiten números y espacios",
                    "oninput": "this.value = this.value.replace(/[^0-9\\s]/g, '')",
                }
            ),
            "correo": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "empresa@correo.com"}
            ),
            "descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Descripción..."}
            ),
        }

    def clean_nit(self):
        nit = self.cleaned_data.get("nit")
        return limpiar_telefono(nit)

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        return limpiar_telefono(telefono)


class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(
            {"class": "form-control", "placeholder": "tu_correo@ejemplo.com"}
        )
        self.fields["email"].label = "Correo Electrónico"


class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "••••••••"}
        )
        self.fields["new_password1"].label = "Nueva Contraseña"

        self.fields["new_password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "••••••••"}
        )
        self.fields["new_password2"].label = "Confirmar Contraseña"


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
