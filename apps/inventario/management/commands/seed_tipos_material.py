"""Carga los tipos de material estándar (catálogo TM001–TM020)."""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.usuarios.models import Catalogo
from core.routers import EnrutadorInventario
from core.utils import conexion_remota_disponible

TIPOS_MATERIAL = [
    ("TM001", "Materiales de Construcción"),
    ("TM002", "Agregados"),
    ("TM003", "Cementos y Morteros"),
    ("TM004", "Aceros y Metales"),
    ("TM005", "Tuberías y Conexiones"),
    ("TM006", "Material Eléctrico"),
    ("TM007", "Material Hidráulico"),
    ("TM008", "Pinturas y Recubrimientos"),
    ("TM009", "Madera y Derivados"),
    ("TM010", "Herramientas"),
    ("TM011", "Equipos de Seguridad (EPP)"),
    ("TM012", "Ferretería General"),
    ("TM013", "Lubricantes y Aceites"),
    ("TM014", "Combustibles"),
    ("TM015", "Repuestos de Vehículos"),
    ("TM016", "Llantas y Accesorios"),
    ("TM017", "Material de Oficina"),
    ("TM018", "Consumibles"),
    ("TM019", "Equipos y Maquinaria"),
    ("TM020", "Señalización y Seguridad Vial"),
]

_router = EnrutadorInventario()


class Command(BaseCommand):
    help = "Inserta o actualiza los 20 tipos de material del catálogo (TM001–TM020)."

    def _databases(self):
        if "remota" in settings.DATABASES and conexion_remota_disponible():
            return ["default", "remota"]
        return ["default"]

    def handle(self, *args, **options):
        total_creados = 0
        total_actualizados = 0

        for db_alias in self._databases():
            self.stdout.write(self.style.NOTICE(f"\n--- Catálogo en: {db_alias} ---"))
            creados = 0
            actualizados = 0

            for codigo, nombre in TIPOS_MATERIAL:
                obj, created = Catalogo.objects.using(db_alias).get_or_create(
                    codigo_catalogo=codigo,
                    defaults={"nombre_empresa": nombre},
                )
                if created:
                    creados += 1
                elif obj.nombre_empresa != nombre:
                    obj.nombre_empresa = nombre
                    obj.save(using=db_alias, update_fields=["nombre_empresa"])
                    actualizados += 1

            total_creados += creados
            total_actualizados += actualizados
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {creados} creados, {actualizados} actualizados "
                    f"({Catalogo.objects.using(db_alias).count()} en total)."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nListo: {total_creados} nuevos, {total_actualizados} actualizados."
            )
        )
