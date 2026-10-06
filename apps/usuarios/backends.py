from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


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
