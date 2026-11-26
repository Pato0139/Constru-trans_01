from django.test import TestCase

from apps.usuarios.forms import LoginForm, RegistroForm
from apps.usuarios.models import Usuario
from apps.usuarios.utils import normalizar_telefono


class RegistroFormTests(TestCase):
    def test_registro_form_valido(self):
        form = RegistroForm(
            data={
                "nombres": "Edward",
                "apellidos": "Fonseca",
                "tipo_documento": "CC",
                "documento": "123456789",
                "pais_codigo": "+57",
                "aceptar_terminos": "yes",
                "telefono": "3001234567",
                "correo": "edward@test.com",
                "contrasena": "Nube!Tren2026#",
                "confirmar_contrasena": "Nube!Tren2026#",
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
                "pais_codigo": "+57",
                "aceptar_terminos": "yes",
                "telefono": "3001234567",
                "correo": "repetido@test.com",
                "contrasena": "Nube!Tren2026#",
                "confirmar_contrasena": "Nube!Tren2026#",
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
                "pais_codigo": "+57",
                "aceptar_terminos": "yes",
                "telefono": "3001234567",
                "correo": "nuevo@test.com",
                "contrasena": "Nube!Tren2026#",
                "confirmar_contrasena": "Nube!Tren2026#",
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
                "pais_codigo": "+57",
                "aceptar_terminos": "yes",
                "telefono": "3001234567",
                "correo": "nuevo@test.com",
                "contrasena": "Pass 1234",
                "confirmar_contrasena": "Pass 1234",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("contrasena", form.errors)

    def test_registro_rechaza_numeros_en_nombres_y_apellidos(self):
        form = RegistroForm(
            data={
                "nombres": "Juan123",
                "apellidos": "Perez",
                "tipo_documento": "CC",
                "documento": "123456789",
                "pais_codigo": "+57",
                "aceptar_terminos": "yes",
                "telefono": "3001234567",
                "correo": "nombre-numerico@test.com",
                "contrasena": "Pass1234",
                "confirmar_contrasena": "Pass1234",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("nombres", form.errors)

    def test_registro_rechaza_inyeccion_en_nombre_documento_y_telefono(self):
        form = RegistroForm(
            data={
                "nombres": "'; DROP TABLE usuario; --",
                "apellidos": "Perez",
                "tipo_documento": "CC",
                "documento": "123456789' OR 1=1 --",
                "pais_codigo": "+57",
                "aceptar_terminos": "yes",
                "telefono": "3001234567; DROP TABLE usuario",
                "correo": "inyeccion@test.com",
                "contrasena": "Pass1234",
                "confirmar_contrasena": "Pass1234",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("nombres", form.errors)
        self.assertIn("documento", form.errors)
        self.assertIn("telefono", form.errors)

    def test_registro_rechaza_codigo_de_pais_manipulado(self):
        form = RegistroForm(
            data={
                "nombres": "Juan",
                "apellidos": "Perez",
                "tipo_documento": "CC",
                "documento": "123456789",
                "pais_codigo": "+999",
                "aceptar_terminos": "yes",
                "telefono": "3001234567",
                "correo": "pais-invalido@test.com",
                "contrasena": "Pass1234",
                "confirmar_contrasena": "Pass1234",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("pais_codigo", form.errors)

    def test_registro_rechaza_omitir_aceptacion_de_terminos(self):
        form = RegistroForm(
            data={
                "nombres": "Juan",
                "apellidos": "Perez",
                "tipo_documento": "CC",
                "documento": "123456789",
                "pais_codigo": "+57",
                "telefono": "3001234567",
                "correo": "sin-terminos@test.com",
                "contrasena": "Nube!Tren2026#",
                "confirmar_contrasena": "Nube!Tren2026#",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("aceptar_terminos", form.errors)


class TelefonoUtilsTests(TestCase):
    def test_normalizar_telefono_agrega_codigo_pais_sin_duplicar(self):
        self.assertEqual(normalizar_telefono("+57", "3001234567"), "+573001234567")
        self.assertEqual(normalizar_telefono("+57", "+573001234567"), "+573001234567")
        self.assertEqual(normalizar_telefono("+57", "57 300 123 4567"), "+573001234567")


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


class LoginCaptchaServerTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username="captcha_tester",
            email="captcha_tester@test.com",
            password="PasswordSeguro123!",
            nombres="Test",
            apellidos="Captcha",
            documento="99887766",
            rol="admin",
            estado="activo",
        )

    def test_reto_captcha_genera_imagen_y_rechaza_codigo_incorrecto(self):
        resp = self.client.get("/usuarios/captcha/reto/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("challenge_id", data)
        self.assertTrue(data["image"].startswith("data:image/png;base64,"))

        bad = self.client.post(
            "/usuarios/captcha/verificar/",
            data={"challenge_id": data["challenge_id"], "answer": "WRONG"},
            content_type="application/json",
        )
        self.assertEqual(bad.status_code, 400)
        bad_data = bad.json()
        self.assertFalse(bad_data["ok"])
        self.assertIn("challenge", bad_data)
        self.assertNotEqual(bad_data["challenge"]["challenge_id"], data["challenge_id"])

    def test_login_rechaza_captcha_checkbox_sin_token_verificado(self):
        resp = self.client.post(
            "/usuarios/login/",
            data={
                "username": "captcha_tester",
                "password": "PasswordSeguro123!",
                "captcha": "on",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_acepta_token_verificado_y_lo_consume_una_sola_vez(self):
        reto_resp = self.client.get("/usuarios/captcha/reto/")
        challenge = self.client.session["login_captcha_challenge"]

        verify_resp = self.client.post(
            "/usuarios/captcha/verificar/",
            data={"challenge_id": challenge["id"], "answer": challenge["answer"]},
            content_type="application/json",
        )
        self.assertEqual(verify_resp.status_code, 200)
        token = verify_resp.json()["token"]

        login_resp = self.client.post(
            "/usuarios/login/",
            data={
                "username": "captcha_tester",
                "password": "PasswordSeguro123!",
                "captcha": "on",
                "captcha_token": token,
            },
        )
        self.assertEqual(login_resp.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

        # El token ya fue consumido; reutilizarlo debe fallar
        self.client.logout()
        replay_resp = self.client.post(
            "/usuarios/login/",
            data={
                "username": "captcha_tester",
                "password": "PasswordSeguro123!",
                "captcha": "on",
                "captcha_token": token,
            },
        )
        self.assertEqual(replay_resp.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
