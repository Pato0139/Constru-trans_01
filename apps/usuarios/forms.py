from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(label="Usuario o Correo", widget=forms.TextInput(attrs={'class': 'input-custom', 'placeholder': 'Usuario o Correo'}))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={'class': 'input-custom', 'placeholder': 'Contraseña', 'id': 'password'}))
    no_robot = forms.BooleanField(label="No soy un robot", required=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

class RegistroForm(forms.Form):
    nombres = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-custom', 'placeholder': 'Juan'}))
    apellidos = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-custom', 'placeholder': 'Pérez'}))
    correo = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'input-custom', 'placeholder': 'ejemplo@correo.com'}))
    tipo_documento = forms.ChoiceField(choices=[('CC', 'C.C.'), ('CE', 'C.E.'), ('NIT', 'NIT')], widget=forms.Select(attrs={'class': 'input-custom form-select'}))
    documento = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-custom', 'placeholder': '12345678'}))
    telefono = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-custom', 'placeholder': '3001234567'}))
    contrasena = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-custom', 'placeholder': '••••••••', 'id': 'id_contrasena'}))
    confirmar_contrasena = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput(attrs={'class': 'input-custom', 'placeholder': '••••••••', 'id': 'id_confirmar_contrasena'}))
    acepto_terminos = forms.BooleanField(label="Acepto los términos y condiciones", required=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    no_robot = forms.BooleanField(label="No soy un robot", required=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
