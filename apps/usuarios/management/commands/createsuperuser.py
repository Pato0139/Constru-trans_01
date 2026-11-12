from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Deshabilitado: no se permite crear superusuarios."

    def handle(self, *args, **options):
        raise CommandError("No se puede crear un superusuario.")
