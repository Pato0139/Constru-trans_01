from django import forms
from django.contrib.auth.models import User
from .models import Usuario, Material, Proveedor

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

    def clean_documento(self):
        documento = self.cleaned_data.get('documento')
        if Usuario.objects.filter(documento=documento).exists():
            raise forms.ValidationError("Este documento ya está registrado.")
        return documento

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("contrasena")
        confirm_password = cleaned_data.get("confirmar_contrasena")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirmar_contrasena', "Las contraseñas no coinciden.")
        return cleaned_data

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['nombre', 'tipo', 'descripcion', 'precio', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: Cemento Gris',
                'style': 'background: #1a1a1a !important; border: 1px solid rgba(255,255,255,0.1) !important;'
            }),
            'tipo': forms.Select(choices=[
                ('', 'Seleccione tipo...'),
                ('Cemento', 'Cemento'),
                ('Arena', 'Arena'),
                ('Grava', 'Grava'),
                ('Ladrillo', 'Ladrillo'),
                ('Herramientas', 'Herramientas'),
            ], attrs={
                'class': 'form-select',
                'style': 'background: #1a1a1a !important; border: 1px solid rgba(255,255,255,0.1) !important;'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Descripción detallada...',
                'style': 'background: #1a1a1a !important; border: 1px solid rgba(255,255,255,0.1) !important;'
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control numeric-only', 
                'step': '0.01',
                'placeholder': '0.00',
                'style': 'background: #1a1a1a !important; border: 1px solid rgba(255,255,255,0.1) !important;'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'style': 'background: #1a1a1a !important; border: 1px solid rgba(255,255,255,0.1) !important;'
            }),
        }

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre_empresa', 'nit', 'contacto_nombre', 'telefono', 'email', 'direccion', 'categoria']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre Legal'}),
            'nit': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '9000000000',
                'pattern': '[0-9\\s]*',
                'title': 'Solo se admiten números y espacios',
                'oninput': "this.value = this.value.replace(/[^0-9\\s]/g, '')"
            }),
            'contacto_nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del asesor'}),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '3001234567',
                'pattern': '[0-9\\s]*',
                'title': 'Solo se admiten números y espacios',
                'oninput': "this.value = this.value.replace(/[^0-9\\s]/g, '')"
            }),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'empresa@correo.com'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección fiscal'}),
            'categoria': forms.Select(choices=[
                ('', 'Seleccione...'),
                ('Materiales', 'Materiales de Construcción'),
                ('Combustible', 'Combustible'),
                ('Repuestos', 'Repuestos y Mantenimiento'),
                ('Servicios', 'Servicios Logísticos'),
            ], attrs={'class': 'form-select'}),
        }
