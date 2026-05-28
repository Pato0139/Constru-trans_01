
import uuid

from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
from django.utils.text import slugify

from .models import Catalogo, MaterialConstruccion, Proveedor, Stock, Usuario
from .utils import limpiar_telefono


class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombres', 'apellidos', 'telefono', 'documento',
                  'tipo_documento', 'rol', 'estado', 'foto_perfil']
        widgets = {
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_documento(self):
        documento = self.cleaned_data.get('documento')
        documento = limpiar_telefono(documento)
        if len(documento) != 10:
            raise forms.ValidationError("El número de documento debe tener exactamente 10 dígitos.")
        # Check if it's already taken by another user
        existing = Usuario.objects.filter(documento=documento)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Este documento ya está registrado.")
        return documento

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        telefono = limpiar_telefono(telefono)
        if len(telefono) != 10:
            raise forms.ValidationError("El número de teléfono debe tener exactamente 10 dígitos.")
        return telefono


class LoginForm(forms.Form):
    username = forms.CharField(label="Usuario o Correo", widget=forms.TextInput(attrs={'class': 'input-custom', 'placeholder': 'Usuario o Correo'}))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={'class': 'input-custom', 'placeholder': 'Contraseña', 'id': 'password'}))


class RegistroForm(forms.ModelForm):
    correo = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'input-custom', 'placeholder': 'ejemplo@correo.com'}))
    contrasena = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-custom', 'placeholder': '••••••••', 'id': 'id_contrasena'}))
    confirmar_contrasena = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput(attrs={'class': 'input-custom', 'placeholder': '••••••••', 'id': 'id_confirmar_contrasena'}))

    class Meta:
        model = Usuario
        fields = ['nombres', 'apellidos', 'tipo_documento', 'documento', 'telefono']
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'input-custom', 'placeholder': 'Juan'}),
            'apellidos': forms.TextInput(attrs={'class': 'input-custom', 'placeholder': 'Pérez'}),
            'tipo_documento': forms.Select(attrs={'class': 'input-custom form-select'}),
            'documento': forms.TextInput(attrs={
                'class': 'input-custom',
                'placeholder': '12345678',
                'pattern': '[0-9\\s]*',
                'title': 'Solo se admiten números y espacios',
                'oninput': "this.value = this.value.replace(/[^0-9\\s]/g, '')"
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'input-custom',
                'placeholder': '3001234567',
                'pattern': '[0-9\\s]*',
                'title': 'Solo se admiten números y espacios',
                'oninput': "this.value = this.value.replace(/[^0-9\\s]/g, '')"
            }),
        }

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if User.objects.filter(email=correo).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return correo

    def clean_contrasena(self):
        contrasena = self.cleaned_data.get('contrasena')
        if ' ' in contrasena:
            raise forms.ValidationError("La contraseña no puede contener espacios.")
        return contrasena

    def clean_documento(self):
        documento = self.cleaned_data.get('documento')
        documento = limpiar_telefono(documento)
        if len(documento) != 10:
            raise forms.ValidationError("El número de documento debe tener exactamente 10 dígitos.")
        if Usuario.objects.filter(documento=documento).exists():
            raise forms.ValidationError("Este documento ya está registrado.")
        return documento

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        telefono = limpiar_telefono(telefono)
        if len(telefono) != 10:
            raise forms.ValidationError("El número de teléfono debe tener exactamente 10 dígitos.")
        return telefono

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("contrasena")
        confirm_password = cleaned_data.get("confirmar_contrasena")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirmar_contrasena', "Las contraseñas no coinciden.")
        return cleaned_data


class MaterialForm(forms.ModelForm):
    tipo = forms.ModelChoiceField(
        queryset=Catalogo.objects.all().order_by('nombre_empresa'),
        required=False,
        label="Tipo de Material",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'style': 'background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;'
        })
    )
    nuevo_tipo = forms.CharField(
        required=False,
        label="Crear nuevo tipo",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Cemento, Acero, Madera',
            'style': 'background: #1a1a1a !important; border: 1px solid rgba(255,255,255,0.1) !important;'
        })
    )
    stock = forms.IntegerField(
        required=False,
        min_value=0,
        label="Stock actual",
        widget=forms.NumberInput(attrs={
            'class': 'form-control numeric-only',
            'placeholder': '0',
            'style': 'background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;'
        })
    )
    ubicacion = forms.CharField(
        required=False,
        label="Ubicación en bodega",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Almacén 1',
            'style': 'background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;'
        })
    )

    class Meta:
        model = MaterialConstruccion
        fields = ['nombre', 'unidad_medida', 'descripcion', 'precio_referencia']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Cemento Gris',
                'style': 'background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;'
            }),
            'unidad_medida': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'kg, m³, unidades, etc.',
                'style': 'background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción detallada...',
                'style': 'background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;'
            }),
            'precio_referencia': forms.TextInput(attrs={
                'class': 'form-control decimal-only',
                'inputmode': 'decimal',
                'placeholder': '0.00',
                'style': 'background: var(--color-surface) !important; color: var(--color-text) !important; border: 1px solid var(--color-border) !important;'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].empty_label = "Seleccione un tipo existente"
        if self.instance and self.instance.pk and self.instance.catalogo:
            self.fields['tipo'].initial = self.instance.catalogo
        if self.instance and self.instance.pk:
            try:
                stock = self.instance.stock_info
                self.fields['stock'].initial = stock.cantidad_actual
                self.fields['ubicacion'].initial = stock.ubicacion
            except Stock.DoesNotExist:
                self.fields['stock'].initial = 0


    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        nuevo_tipo = cleaned_data.get('nuevo_tipo')

        if tipo and nuevo_tipo:
            raise forms.ValidationError("Elija un tipo existente o cree uno nuevo, no ambos.")
        if not tipo and not nuevo_tipo:
            raise forms.ValidationError("Seleccione un tipo existente o cree uno nuevo.")

        return cleaned_data

    def save(self, commit=True):
        material = super().save(commit=False)
        tipo = self.cleaned_data.get('tipo')
        nuevo_tipo = self.cleaned_data.get('nuevo_tipo')

        if nuevo_tipo:
            nombre = nuevo_tipo.strip()
            catalogo = Catalogo.objects.filter(nombre_empresa__iexact=nombre).first()
            if not catalogo:
                catalogo = Catalogo.objects.create(
                    codigo_catalogo=self._generate_catalogo_code(nombre),
                    nombre_empresa=nombre
                )
            material.catalogo = catalogo
        else:
            material.catalogo = tipo

        if commit:
            material.save()

        stock_value = self.cleaned_data.get('stock')
        ubicacion = self.cleaned_data.get('ubicacion', '')

        if stock_value is not None:
            stock_obj, created = Stock.objects.get_or_create(
                material=material,
                defaults={
                    'cantidad_actual': stock_value,
                    'ubicacion': ubicacion or '',
                }
            )
            if not created:
                stock_obj.cantidad_actual = stock_value
                stock_obj.ubicacion = ubicacion or stock_obj.ubicacion
                stock_obj.save()

        return material

    def _generate_catalogo_code(self, nombre):
        base_code = slugify(nombre).upper().replace('-', '_')[:16] or 'CATALOGO'
        code = base_code
        counter = 1
        while Catalogo.objects.filter(codigo_catalogo=code).exists():
            suffix = f"_{counter}"
            trimmed = base_code[:20 - len(suffix)]
            code = f"{trimmed}{suffix}"
            counter += 1
        return code


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre_empresa', 'nit', 'telefono', 'correo', 'descripcion']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre Legal'}),
            'nit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '9000000000',
                'pattern': '[0-9\\s]*',
                'title': 'Solo se admiten números y espacios',
                'oninput': "this.value = this.value.replace(/[^0-9\\s]/g, '')"
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '3001234567',
                'pattern': '[0-9\\s]*',
                'title': 'Solo se admiten números y espacios',
                'oninput': "this.value = this.value.replace(/[^0-9\\s]/g, '')"
            }),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'empresa@correo.com'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción...'}),
        }

    def clean_nit(self):
        nit = self.cleaned_data.get('nit')
        return limpiar_telefono(nit)

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        return limpiar_telefono(telefono)


class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'tu_correo@ejemplo.com'
        })
        self.fields['email'].label = 'Correo Electrónico'


class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '••••••••'
        })
        self.fields['new_password1'].label = 'Nueva Contraseña'

        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '••••••••'
        })
        self.fields['new_password2'].label = 'Confirmar Contraseña'

