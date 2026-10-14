from types import SimpleNamespace

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import SimpleTestCase

from apps.licensing.admin import _SoloSuperadminModifica
from apps.licensing.models import Licencia
from apps.usuarios.backends import AdminRolePermissionBackend
from apps.usuarios.models import Usuario
from apps.usuarios.models_permisos import usuario_tiene_permiso
from config.admin_site import (
    ConstruTransAdminAuthenticationForm,
    ConstruTransAdminSite,
)
from config.superadmin_lock import SUPERADMIN_EMAIL, SUPERADMIN_USERNAME


class AdminRoleAccessTests(SimpleTestCase):
    def setUp(self):
        self.backend = AdminRolePermissionBackend()
        self.site = ConstruTransAdminSite(name="test_admin")
        self.admin_user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_staff=False,
            is_superuser=False,
            email="admin@example.com",
            username="admin",
            rol="admin",
        )

    def test_active_business_admin_can_enter_admin_site_without_staff(self):
        request = SimpleNamespace(user=self.admin_user)

        self.assertTrue(self.site.has_permission(request))

    def test_admin_login_form_accepts_active_role_admin_without_staff(self):
        form = ConstruTransAdminAuthenticationForm()

        self.assertIsNone(form.confirm_login_allowed(self.admin_user))

    def test_admin_login_form_rejects_non_admin_without_staff(self):
        user = SimpleNamespace(is_active=True, is_staff=False, rol="cliente")
        form = ConstruTransAdminAuthenticationForm()

        with self.assertRaises(ValidationError):
            form.confirm_login_allowed(user)

    def test_business_admin_gets_regular_model_permissions(self):
        self.assertTrue(
            self.backend.has_perm(
                self.admin_user, "catalogo.change_materialconstruccion"
            )
        )

    def test_permission_backend_grants_only_non_sensitive_model_access(self):
        user = Usuario(
            username="admin",
            email="admin@example.com",
            rol="admin",
            is_active=True,
            is_staff=False,
        )

        self.assertTrue(user.has_perm("catalogo.change_materialconstruccion"))
        self.assertFalse(user.has_perm("licensing.change_licencia"))
        self.assertFalse(user.has_module_perms("licensing"))

    def test_business_admin_has_all_operational_functions(self):
        self.assertTrue(usuario_tiene_permiso(self.admin_user, "registrar_novedad"))

    def test_business_admin_cannot_manage_licenses_or_permission_models(self):
        restricted_permissions = (
            "licensing.change_licencia",
            "usuarios.change_rolpermiso",
            "auth.change_group",
            "usuarios.change_usuario",
        )

        for permission in restricted_permissions:
            with self.subTest(permission=permission):
                with self.assertRaises(PermissionDenied):
                    self.backend.has_perm(self.admin_user, permission)

    def test_only_global_admin_can_modify_license_records(self):
        model_admin = _SoloSuperadminModifica(Licencia, self.site)
        request = SimpleNamespace(user=self.admin_user)
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))

        global_admin = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
            is_staff=True,
            email=SUPERADMIN_EMAIL,
            username=SUPERADMIN_USERNAME,
        )
        request.user = global_admin
        self.assertTrue(model_admin.has_add_permission(request))
        self.assertTrue(model_admin.has_change_permission(request))
        self.assertTrue(model_admin.has_delete_permission(request))

    def test_non_admin_does_not_receive_role_permissions(self):
        user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_superuser=False,
            email="user@example.com",
            username="user",
            rol="cliente",
        )

        self.assertFalse(
            self.backend.has_perm(user, "catalogo.change_materialconstruccion")
        )
