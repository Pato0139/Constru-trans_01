"""Generación de consecutivos sin condiciones de carrera.

Se usa una fila contador por (prefijo, año) bloqueada con SELECT ... FOR UPDATE
dentro de una transacción. Además, la columna destino debe tener UNIQUE para
que la base de datos sea la última barrera.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from config.db_utils import select_for_update_if_supported


def siguiente_consecutivo(prefijo, anio=None, using="default"):
    from config.models import Consecutivo

    anio = anio or timezone.now().year
    with transaction.atomic(using=using):
        qs = Consecutivo.objects.using(using)
        try:
            contador = select_for_update_if_supported(qs, using).get(prefijo=prefijo, anio=anio)
        except Consecutivo.DoesNotExist:
            try:
                with transaction.atomic(using=using):
                    contador = qs.create(prefijo=prefijo, anio=anio, ultimo=0)
            except IntegrityError:
                # Otra transacción lo creó en paralelo: bloquear la existente.
                pass
            contador = select_for_update_if_supported(qs, using).get(prefijo=prefijo, anio=anio)
        contador.ultimo += 1
        contador.save(using=using, update_fields=["ultimo"])
        return contador.ultimo


def numero_factura(anio=None, using="default"):
    anio = anio or timezone.now().year
    n = siguiente_consecutivo("F", anio, using=using)
    return f"F-{anio}-{n:05d}"
