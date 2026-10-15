from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.usuarios.models_permisos import usuario_tiene_permiso


class PermisosLicenciaTests(SimpleTestCase):
    def test_admin_obtiene_funcion_de_una_licencia_vigente(self):
        permission_codename = "licencia_registrar_novedad"
        license_permissions = MagicMock()
        license_permissions.values_list.return_value = [permission_codename]
        licencia = SimpleNamespace(
            esta_vigente=True,
            permisos=license_permissions,
        )
        asignacion = SimpleNamespace(licencia=licencia)
        user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            email="admin@example.com",
            username="admin",
            pk=1,
        )

        with (
            patch(
                "apps.usuarios.models_permisos.PermisoUsuario.objects.filter"
            ) as direct_permissions,
            patch(
                "apps.usuarios.models_permisos.UsuarioRolNegocio.objects.filter"
            ) as user_roles,
            patch(
                "apps.licensing.models.UsuarioLicencia.objects.filter",
            ) as user_licenses,
            patch(
                "apps.usuarios.models_permisos.Permiso.objects.filter",
                return_value=[SimpleNamespace(codename=permission_codename)],
            ),
        ):
            direct_permissions.return_value.exists.return_value = False
            user_roles.return_value.values_list.return_value = []
            user_licenses.return_value.select_related.return_value = [asignacion]

            self.assertTrue(usuario_tiene_permiso(user, "registrar_novedad"))
