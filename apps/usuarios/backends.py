from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from config.superadmin_lock import es_superadmin_global

User = get_user_model()


class AdminRolePermissionBackend(ModelBackend):
    """
    Backend de autenticación + control de permisos del /admin/.

    Extiende ModelBackend (hereda authenticate/get_user) y ademas restringe
    que solo el Administrador Global toque permisos, roles, licencias y
    usuarios desde /admin/, levantando PermissionDenied en los modelos
    protegidos.

    Nota: debe estar en AUTHENTICATION_BACKENDS y por eso necesita authenticate;
    antes era una clase plana sin ese metodo -> AttributeError al hacer login.
    """

    PROTECTED_APPS = {"auth", "contenttypes"}
    PROTECTED_MODELS = {
        ("usuarios", "permiso"),
        ("usuarios", "permisousuario"),
        ("usuarios", "rol"),
        ("usuarios", "rolpermiso"),
        ("usuarios", "rolproxy"),
        ("usuarios", "usuariorol"),
        ("usuarios", "usuariorolnegocio"),
    }

    def has_perm(self, user_obj, perm, obj=None):
        if not getattr(user_obj, "is_authenticated", False) or not getattr(
            user_obj, "is_active", False
        ):
            return False
        if es_superadmin_global(user_obj):
            return False

        app_label, separator, codename = perm.partition(".")
        if not separator:
            return False

        if app_label in self.PROTECTED_APPS:
            raise PermissionDenied("Solo el Administrador Global puede modificar permisos.")
        if app_label == "licensing" and getattr(user_obj, "rol", None) == "admin":
            raise PermissionDenied("Solo el Administrador Global puede gestionar licencias.")

        action, separator, model_name = codename.partition("_")
        if separator and (app_label, model_name) in self.PROTECTED_MODELS:
            raise PermissionDenied("Solo el Administrador Global puede modificar roles y permisos.")
        if app_label == "usuarios" and model_name == "usuario":
            if action != "view":
                raise PermissionDenied(
                    "Solo el Administrador Global puede modificar usuarios desde /admin/."
                )

        return getattr(user_obj, "rol", None) == "admin"

    def has_module_perms(self, user_obj, app_label):
        if not getattr(user_obj, "is_authenticated", False) or not getattr(
            user_obj, "is_active", False
        ):
            return False
        if es_superadmin_global(user_obj):
            return False
        if app_label in self.PROTECTED_APPS:
            raise PermissionDenied("Solo el Administrador Global puede gestionar permisos.")
        if app_label == "licensing" and getattr(user_obj, "rol", None) == "admin":
            raise PermissionDenied("Solo el Administrador Global puede gestionar licencias.")
        return getattr(user_obj, "rol", None) == "admin"


class EmailOrUsernameBackend(ModelBackend):
    """
    Permite autenticar con username o email indistintamente.

    Mejoras sobre ModelBackend:
    1. Busca al usuario por (username == identifier) O (email == identifier) en un solo query.
    2. Acepta identificador case-insensitive (email/username normalizados).
    3. Rechaza explícitamente usuarios con estado inactivo/suspendido aunque is_active
       estuviera desalineado (doble check; el sync en Usuario.save() ya lo previene).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        identifier = username.strip()
        try:
            user = User.objects.filter(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            ).first()
        except User.DoesNotExist:
            return None

        if user is None:
            User().set_password(password)
            return None

        if not user.check_password(password):
            return None

        # Doble validación: is_active (Django default) Y estado (proyecto custom)
        if not (getattr(user, "is_active", True) and getattr(user, "estado", "activo") == "activo"):
            return None

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
