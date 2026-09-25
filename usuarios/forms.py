from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.db.models import Q

User = get_user_model()

from .models import Usuario
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

        existing = Usuario.objects.using("default").filter(documento=documento)
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
        if User.objects.using("default").filter(email=correo).exists():
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
        if Usuario.objects.using("default").filter(documento=documento).exists():
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


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.CharField(
        label="Usuario o Correo Electrónico",
        max_length=254,
        widget=forms.TextInput(attrs={
            "class": "input-custom",
            "placeholder": "Ingresa tu usuario o correo electrónico",
            "autofocus": True
        })
    )

    def get_users(self, email):
        from django.conf import settings
        from core.utils import conexion_remota_disponible
        seen = set()
        merged = []
        criterio = Q(email__iexact=email) | Q(username__iexact=email)
        qs_local = list(User.objects.filter(criterio, is_active=True).using("default"))
        qs_remota = []
        if "remota" in settings.DATABASES and conexion_remota_disponible():
            try:
                qs_remota = list(User.objects.filter(criterio, is_active=True).using("remota"))
            except Exception:
                qs_remota = []
        for obj in qs_local + qs_remota:
            dedup_key = (
                (obj.email or "").lower(),
                (obj.username or "").lower(),
            )
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            if obj.has_usable_password():
                merged.append(obj)
        return iter(merged)
