"""
Pruebas de integración para los perfiles unificados de:
  - Administrador (/usuarios/perfil/admin/)
  - Cliente (/clientes/perfil/)
  - Conductor (/usuarios/perfil-conductor/)
Y sus funciones:
  - Cambio de foto de perfil con retorno a la vista de perfil
  - Cambio de contraseña en sitio (validando clave actual y manteniendo sesión)
  - Sincronización manual de base local para administradores
"""

import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from apps.clientes.models import Cliente
from apps.usuarios.models import Conductor, Usuario


def _make_test_png():
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (26, 115, 232)).save(buf, format="PNG")
    return SimpleUploadedFile("avatar_test.png", buf.getvalue(), content_type="image/png")


class PerfilesUnificadosTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="Edward_Fonseca",
            email="edwardf5432@gmail.com",
            password="PasswordAdmin123!",
            nombres="Edward",
            apellidos="Fonseca",
            documento="10101010",
            telefono="3001234567",
            rol="admin",
            estado="activo",
            is_staff=True,
            is_superuser=True,
        )
        self.cliente_user = Usuario.objects.create_user(
            username="maria_cli",
            email="maria_cli@test.com",
            password="PasswordCliente123!",
            nombres="Maria",
            apellidos="Perez",
            documento="20202020",
            telefono="3002223344",
            rol="cliente",
            estado="activo",
        )
        Cliente.objects.get_or_create(usuario=self.cliente_user)

        self.conductor_user = Usuario.objects.create_user(
            username="carlos_cond",
            email="carlos_cond@test.com",
            password="PasswordCond123!",
            nombres="Carlos",
            apellidos="Lopez",
            documento="30303030",
            telefono="3005556677",
            rol="conductor",
            estado="activo",
        )
        Conductor.ensure_for_user(self.conductor_user)

    def _login(self, user):
        self.client.force_login(user)
        s = self.client.session
        s["session_version"] = user.session_version
        s.save()

    def test_perfil_admin_renderiza_info_y_gestion_sistema(self):
        self._login(self.admin)
        resp = self.client.get("/usuarios/perfil/admin/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Edward Fonseca")
        self.assertContains(resp, "Gestión de Sistema")
        self.assertContains(resp, "Sincronizar Base Local")
        self.assertContains(resp, "Cambiar Contraseña")

    def test_perfil_cliente_renderiza_info_y_resumen_cuenta(self):
        self._login(self.cliente_user)
        resp = self.client.get("/clientes/perfil/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Maria Perez")
        self.assertContains(resp, "Resumen de mi Cuenta")
        self.assertContains(resp, "Nuevo Pedido")
        self.assertContains(resp, "Cambiar Contraseña")

    def test_perfil_conductor_renderiza_info_y_operacion_flota(self):
        self._login(self.conductor_user)
        resp = self.client.get("/usuarios/perfil-conductor/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Carlos Lopez")
        self.assertContains(resp, "Operación y Flota")
        self.assertContains(resp, "Vehículo Asignado")
        self.assertContains(resp, "Cambiar Contraseña")

    def test_subir_foto_desde_perfil_guarda_y_redirige_al_perfil(self):
        self._login(self.admin)
        resp = self.client.post(
            "/usuarios/perfil/editar/",
            {
                "action": "upload_photo",
                "next": "/usuarios/perfil/admin/",
                "foto_perfil": _make_test_png(),
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/usuarios/perfil/admin/")
        self.admin.refresh_from_db()
        self.assertTrue(bool(self.admin.foto_perfil.name))

    def test_cambiar_password_perfil_rechaza_actual_incorrecta_y_actualiza_cuando_es_valida(self):
        self._login(self.cliente_user)

        bad = self.client.post(
            "/usuarios/perfil/cambiar-password/",
            {
                "old_password": "Incorrecta999!",
                "new_password1": "NuevaClaveSegura456!",
                "new_password2": "NuevaClaveSegura456!",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(bad.status_code, 400)
        self.assertFalse(bad.json()["ok"])

        ok = self.client.post(
            "/usuarios/perfil/cambiar-password/",
            {
                "old_password": "PasswordCliente123!",
                "new_password1": "NuevaClaveSegura456!",
                "new_password2": "NuevaClaveSegura456!",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.json()["ok"])

        self.cliente_user.refresh_from_db()
        self.assertTrue(self.cliente_user.check_password("NuevaClaveSegura456!"))

    def test_sincronizar_bd_local_solo_admin_y_devuelve_resumen(self):
        # Cliente no puede sincronizar BD local
        self._login(self.cliente_user)
        forbidden = self.client.post(
            "/usuarios/bd/sincronizar/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertIn(forbidden.status_code, (302, 403))

        # Admin sí puede
        self._login(self.admin)
        with (
            patch("apps.usuarios.views.conexion_remota_disponible", return_value=True),
            patch(
                "config.sync_local.sincronizar_cambios_remota_a_local",
                return_value={"tablas_actualizadas": 2, "registros_descargados": 5},
            ),
        ):
            ok = self.client.post(
                "/usuarios/bd/sincronizar/",
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
        self.assertEqual(ok.status_code, 200)
        data = ok.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["registros_descargados"], 5)
