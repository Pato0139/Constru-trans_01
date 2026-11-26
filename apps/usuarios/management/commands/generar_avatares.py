"""
Comando: python manage.py generar_avatares

Genera y asigna avatares estilo Google (inicial + color único) para todos los
usuarios registrados que no tengan foto de perfil o cuyo archivo no exista en disco.
Actualiza tanto local ('default') como nube ('remota') si está disponible.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.usuarios.avatars import asegurar_avatar_usuario
from apps.usuarios.models import Usuario
from config.utils import conexion_remota_disponible


class Command(BaseCommand):
    help = "Genera fotos de perfil estilo Google (inicial + color) para todos los usuarios sin foto."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenera el avatar incluso si el usuario ya tiene uno.",
        )

    def handle(self, *args, **options):
        force = bool(options.get("force", False))
        remota_ok = "remota" in settings.DATABASES and conexion_remota_disponible()

        generados = 0
        usuarios = list(Usuario._base_manager.using("default").all().order_by("pk"))

        for usuario in usuarios:
            creado = asegurar_avatar_usuario(usuario, using="default", force=force)
            if creado:
                generados += 1
                if remota_ok:
                    try:
                        Usuario._base_manager.using("remota").filter(pk=usuario.pk).update(
                            foto_perfil=usuario.foto_perfil.name
                        )
                    except Exception:
                        pass

        self.stdout.write(
            self.style.SUCCESS(
                f"Avatares generados/actualizados: {generados} de {len(usuarios)} usuarios "
                f"(remota sincronizada: {'Sí' if remota_ok else 'No'})."
            )
        )
