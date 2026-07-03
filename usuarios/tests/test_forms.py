from django.test import TestCase

from usuarios.forms import LoginForm, RegistroForm
from usuarios.models import Usuario


class RegistroFormTests(TestCase):
    def test_registro_form_valido(self):
        form = RegistroForm(
            data={
                "nombres": "Edward",
                "apellidos": "Fonseca",
                "tipo_documento": "CC",
                "documento": "123456789",
                "telefono": "3001234567",
                "correo": "edward@test.com",
                "contrasena": "Pass1234",
                "confirmar_contrasena": "Pass1234",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_registro_form_rechaza_correo_duplicado(self):
        Usuario.objects.create_user(
            username="existente",
            email="repetido@test.com",
            password="password123",
            nombres="Existente",
            apellidos="Uno",
            documento="111111111",
            tipo_documento="CC",
            rol="cliente",
        )
        form = RegistroForm(
            data={
                "nombres": "Nuevo",
                "apellidos": "Usuario",
                "tipo_documento": "CC",
                "documento": "222222222",
                "telefono": "3001234567",
                "correo": "repetido@test.com",
                "contrasena": "Pass1234",
                "confirmar_contrasena": "Pass1234",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("correo", form.errors)

    def test_registro_form_rechaza_documento_invalido(self):
        form = RegistroForm(
            data={
                "nombres": "Nuevo",
                "apellidos": "Usuario",
                "tipo_documento": "CC",
                "documento": "ABC123",
                "telefono": "3001234567",
                "correo": "nuevo@test.com",
                "contrasena": "Pass1234",
                "confirmar_contrasena": "Pass1234",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("documento", form.errors)

    def test_registro_form_rechaza_password_con_espacios(self):
        form = RegistroForm(
            data={
                "nombres": "Nuevo",
                "apellidos": "Usuario",
                "tipo_documento": "CC",
                "documento": "123456789",
                "telefono": "3001234567",
                "correo": "nuevo@test.com",
                "contrasena": "Pass 1234",
                "confirmar_contrasena": "Pass 1234",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("contrasena", form.errors)


class LoginFormTests(TestCase):
    def test_login_form_exige_captcha(self):
        form = LoginForm(
            data={
                "username": "admin@test.com",
                "password": "password123",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("captcha", form.errors)
