from django.conf import settings
from django.core.management.base import BaseCommand

from core.routers import EnrutadorInventario
from core.utils import conexion_remota_disponible
from usuarios.models import Catalogo

_router = EnrutadorInventario()


class Command(BaseCommand):
    help = "Carga tipos de material estándar para el catálogo de inventario."

    def _databases_to_seed(self):
        if "remota" in settings.DATABASES and conexion_remota_disponible():
            return ["remota", "default"]
        return ["default"]

    def _get_or_create_catalogo(self, db_alias, codigo, nombre):
        catalogo, created = Catalogo.objects.using(db_alias).update_or_create(
            codigo_catalogo=codigo,
            defaults={"nombre_empresa": nombre},
        )
        return catalogo, created

    def handle(self, *args, **options):
        tipos_data = [
            {"codigo": "ARE", "nombre": "Arenas y Grava"},
            {"codigo": "CEM", "nombre": "Cementos y Hormigón"},
            {"codigo": "MAD", "nombre": "Maderas y Tableros"},
            {"codigo": "FER", "nombre": "Ferretería y Tornillería"},
            {"codigo": "ACB", "nombre": "Acabados y Revestimientos"},
            {"codigo": "HID", "nombre": "Hidrosanitarios"},
            {"codigo": "PIN", "nombre": "Pinturas y Barnices"},
            {"codigo": "ELC", "nombre": "Eléctricos y Accesorios"},
            {"codigo": "HER", "nombre": "Herramientas y Maquinaria"},
            {"codigo": "VID", "nombre": "Vidrios y Cerámicas"},
            {"codigo": "ADH", "nombre": "Adhesivos y Selladores"},
            {"codigo": "SEG", "nombre": "Seguridad y Protecciones"},
        ]

        databases = self._databases_to_seed()
        self.stdout.write(self.style.NOTICE("\n--- Cargando tipos de material estándar ---"))

        for db_alias in databases:
            created_count = 0
            updated_count = 0
            self.stdout.write(self.style.NOTICE(f"\nBase de datos: {db_alias}"))

            for tipo in tipos_data:
                catalogo, created = self._get_or_create_catalogo(
                    db_alias, tipo["codigo"], tipo["nombre"]
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"✓ Creado: {catalogo.codigo_catalogo} - {catalogo.nombre_empresa}"))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f"↻ Actualizado: {catalogo.codigo_catalogo} - {catalogo.nombre_empresa}"))

            self.stdout.write(
                self.style.SUCCESS(
                    f"Resumen {db_alias}: {created_count} creados, {updated_count} actualizados"
                )
            )

        self.stdout.write(self.style.SUCCESS("\nTipos de material estándar cargados correctamente."))
