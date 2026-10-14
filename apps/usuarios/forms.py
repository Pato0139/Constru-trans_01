import logging
import smtplib

import requests
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.core.mail import EmailMultiAlternatives
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from django.template import loader

User = get_user_model()
logger = logging.getLogger(__name__)

from .models import Usuario
from .utils import limpiar_telefono


class FotoPerfilForm(forms.Form):
    foto_perfil = forms.ImageField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])],
    )

    def clean_foto_perfil(self):
        foto = self.cleaned_data.get("foto_perfil")
        if foto and foto.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La foto debe pesar máximo 5 MB.")
        return foto


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
        from config.utils import conexion_remota_disponible

        seen = set()
        merged = []
        criterio = Q(email__iexact=email) | Q(username__iexact=email)
        qs_local = list(User.objects.filter(criterio, is_active=True).using("default"))
        qs_remota = []
        if "remota" in settings.DATABASES and conexion_remota_disponible():
            try:
                qs_remota = list(User.objects.filter(criterio, is_active=True).using("remota"))
            except Exception as exc:
                logger.warning(
                    "Password reset could not query the remote user database (%s)",
                    type(exc).__name__,
                )
        for obj in qs_local + qs_remota:
            dedup_key = (
                (obj.email or "").lower(),
                (obj.username or "").lower(),
            )
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            if obj.has_usable_password() and obj.email:
                merged.append(obj)
        logger.info(
            "Password reset matched %d active account(s) with email and usable password",
            len(merged),
        )
        return iter(merged)

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        api_key = settings.RESEND_API_KEY.strip()
        sender = settings.RESEND_FROM_EMAIL.strip()
        subject = loader.render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)
        html_body = (
            loader.render_to_string(html_email_template_name, context)
            if html_email_template_name is not None
            else None
        )

        if not api_key or not sender:
            message = EmailMultiAlternatives(
                subject,
                body,
                from_email,
                [to_email],
            )
            if html_body is not None:
                message.attach_alternative(html_body, "text/html")
            return message.send(fail_silently=False)

        payload = {
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "text": body,
        }
        if html_body is not None:
            payload["html"] = html_body

        try:
            response = requests.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=(5, 15),
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning(
                "Resend password-reset request failed (%s, HTTP %s)",
                type(exc).__name__,
                getattr(getattr(exc, "response", None), "status_code", "n/a"),
            )
            raise smtplib.SMTPException(
                "Resend could not accept the password-reset email"
            ) from exc

        try:
            message_id = response.json().get("id")
        except (ValueError, AttributeError):
            message_id = None
        logger.info(
            "Resend accepted a password-reset email (message_id=%s)",
            message_id or "unavailable",
        )
        return 1
