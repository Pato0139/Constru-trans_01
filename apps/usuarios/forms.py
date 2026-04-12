from django import forms
from .models import Usuario

class LoginForm(forms.Form):
    username = forms.CharField(label="Usuario o Correo", widget=forms.TextInput(attrs={'class': 'input-custom', 'placeholder': 'Usuario o Correo'}))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={'class': 'input-custom', 'placeholder': 'Contraseña', 'id': 'password'}))
    no_robot = forms.BooleanField(label="No soy un robot", required=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

class RegistroForm(forms.Form):
    nombres = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-custom', 'placeholder': 'Juan'}))
    apellidos = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-custom', 'placeholder': 'Pérez'}))
    correo = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'input-custom', 'placeholder': 'ejemplo@correo.com'}))
    tipo_documento = forms.ChoiceField(choices=Usuario.TIPOS_DOCUMENTO, widget=forms.Select(attrs={'class': 'input-custom form-select'}))
    documento = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'input-custom', 
        'placeholder': '12345678',
        'oninput': "this.value = this.value.replace(/[^0-9]/g, '');",
        'maxlength': '20'
    }))
    telefono = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'input-custom', 
        'placeholder': '3001234567',
        'oninput': "this.value = this.value.replace(/[^0-9]/g, '');",
        'maxlength': '15'
    }))
    contrasena = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-custom', 'placeholder': '••••••••'}))
    confirmar_contrasena = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput(attrs={'class': 'input-custom', 'placeholder': '••••••••'}))
    acepto_terminos = forms.BooleanField(label="Acepto los términos y condiciones", required=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    no_robot = forms.BooleanField(label="No soy un robot", required=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    def clean_documento(self):
        documento = self.cleaned_data.get('documento')
        if not documento.isdigit():
            raise forms.ValidationError("El número de identificación debe contener solo números.")
        return documento

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not telefono.isdigit():
            raise forms.ValidationError("El número de teléfono debe contener solo números.")
        return telefono

    def clean(self):
        cleaned_data = super().clean()
        contrasena = cleaned_data.get("contrasena")
        confirmar_contrasena = cleaned_data.get("confirmar_contrasena")

        if contrasena and confirmar_contrasena and contrasena != confirmar_contrasena:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data
