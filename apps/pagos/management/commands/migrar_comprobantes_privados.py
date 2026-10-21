import os
import shutil
import uuid
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.pagos.models import Pago, PagoFactura


class Command(BaseCommand):
    help = (
        "Migra, respalda y renombra comprobantes existentes a UUIDv4 hexadecimal "
        "para eliminar nombres originales predecibles o expuestos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--ejecutar",
            action="store_true",
            help="Ejecuta la migración en disco y base de datos (por defecto es simulación --dry-run).",
        )
        parser.add_argument(
            "--backup-dir",
            type=str,
            default="",
            help="Directorio de destino para el respaldo de seguridad previo a la migración.",
        )

    def handle(self, *args, **options):
        ejecutar = options.get("ejecutar", False)
        backup_dir = options.get("backup_dir")

        self.stdout.write(self.style.MIGRATE_HEADING("=== MIGRACIÓN DE COMPROBANTES A UUID ==="))
        if not ejecutar:
            self.stdout.write(self.style.WARNING("MODO SIMULACIÓN (DRY-RUN): No se aplicarán cambios en disco ni en BD."))
            self.stdout.write("Use --ejecutar para aplicar los cambios.")

        media_root = Path(settings.MEDIA_ROOT)
        comprobantes_dir = media_root / "comprobantes"

        # 1. Respaldo previo obligatorio si se ejecuta
        if ejecutar:
            dest_backup = Path(backup_dir) if backup_dir else media_root / f"backup_comprobantes_{uuid.uuid4().hex[:8]}"
            if comprobantes_dir.exists():
                self.stdout.write(f"Creando respaldo en: {dest_backup} ...")
                shutil.copytree(comprobantes_dir, dest_backup, dirs_exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f"Respaldo completado en {dest_backup}"))
            else:
                self.stdout.write(self.style.NOTICE("No existe directorio comprobantes en MEDIA_ROOT; omitiendo copia física."))

        # 2. Migración de Pago (comprobante)
        pagos = Pago.objects.exclude(comprobante="").exclude(comprobante__isnull=True)
        total_pagos = pagos.count()
        renombrados_pagos = 0
        ya_conformes_pagos = 0

        self.stdout.write(f"\nAnalizando {total_pagos} registros de Pago...")
        for p in pagos:
            nombre_actual = p.comprobante.name
            path_partes = Path(nombre_actual)
            nombre_archivo = path_partes.name
            stem = path_partes.stem
            ext = path_partes.suffix.lower() or ".jpg"

            # Si ya es un UUID hex de 32 caracteres, está conforme
            es_uuid = len(stem) == 32 and all(c in "0123456789abcdefABCDEF" for c in stem)
            if es_uuid:
                ya_conformes_pagos += 1
                continue

            nuevo_stem = uuid.uuid4().hex
            nuevo_nombre_rel = f"comprobantes/pedido_{p.pedido_id}/{nuevo_stem}{ext}"

            self.stdout.write(f"  [Pago pk={p.pk}] {nombre_actual} -> {nuevo_nombre_rel}")

            if ejecutar:
                ruta_antigua = media_root / nombre_actual
                ruta_nueva = media_root / nuevo_nombre_rel
                if ruta_antigua.exists():
                    ruta_nueva.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(ruta_antigua, ruta_nueva)
                p.comprobante.name = nuevo_nombre_rel
                p.save(update_fields=["comprobante"])
            renombrados_pagos += 1

        # 3. Migración de PagoFactura (evidencia)
        pagos_fac = PagoFactura.objects.exclude(evidencia="").exclude(evidencia__isnull=True)
        total_pagos_fac = pagos_fac.count()
        renombrados_fac = 0
        ya_conformes_fac = 0

        self.stdout.write(f"\nAnalizando {total_pagos_fac} registros de PagoFactura...")
        for pf in pagos_fac:
            nombre_actual = pf.evidencia.name
            path_partes = Path(nombre_actual)
            stem = path_partes.stem
            ext = path_partes.suffix.lower() or ".jpg"

            es_uuid = len(stem) == 32 and all(c in "0123456789abcdefABCDEF" for c in stem)
            if es_uuid:
                ya_conformes_fac += 1
                continue

            nuevo_stem = uuid.uuid4().hex
            nuevo_nombre_rel = f"comprobantes/factura_{pf.factura_id}/{nuevo_stem}{ext}"

            self.stdout.write(f"  [PagoFactura pk={pf.pk}] {nombre_actual} -> {nuevo_nombre_rel}")

            if ejecutar:
                ruta_antigua = media_root / nombre_actual
                ruta_nueva = media_root / nuevo_nombre_rel
                if ruta_antigua.exists():
                    ruta_nueva.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(ruta_antigua, ruta_nueva)
                pf.evidencia.name = nuevo_nombre_rel
                pf.save(update_fields=["evidencia"])
            renombrados_fac += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nResumen: {renombrados_pagos} Pagos por migrar/migrados, {ya_conformes_pagos} ya conformes. "
            f"{renombrados_fac} PagoFacturas por migrar/migrados, {ya_conformes_fac} ya conformes."
        ))
