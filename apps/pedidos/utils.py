import logging
from datetime import timedelta
from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models.deletion import Collector, ProtectedError
from django.db.models import F
from django.utils import timezone

from apps.catalogo.models import MaterialConstruccion, Stock
from apps.catalogo.models.movimientos import MovimientoInventario
from config.db_preference import debe_usar_bd_remota
from config.db_utils import select_for_update_if_supported

logger = logging.getLogger(__name__)


def pedido_tiene_pago_recibido(pedido):
    """Admite contraentrega o un comprobante físicamente disponible."""
    from apps.pagos.models import Pago

    pago = getattr(pedido, "pago_actual", None)
    if pago is None:
        return False
    if pago.metodo == Pago.METODO_CONTRAENTREGA:
        return True
    if not pago.requiere_comprobante():
        return False
    return pago.comprobante_existe_en_disco


def filtrar_pedidos_con_pago_recibido(pedidos, *, limite=None):
    """Filtra usando existencia real del archivo, no solo la ruta guardada en BD."""
    from django.db.models import Q
    from apps.pagos.models import Pago

    candidatos = pedidos.filter(
        Q(pago__metodo=Pago.METODO_CONTRAENTREGA) | Q(pago__comprobante__gt="")
    ).select_related("pago")
    recibidos = []
    for pedido in candidatos:
        if pedido_tiene_pago_recibido(pedido):
            recibidos.append(pedido)
            if limite is not None and len(recibidos) >= limite:
                break
    return recibidos


def revertir_stock_pedido(orden, usuario, motivo_prefijo="Cancelación", using=None):
    db_alias = using if using else ("remota" if debe_usar_bd_remota() else "default")
    detalles = list(orden.detalles.using(db_alias).all())
    materiales = MaterialConstruccion.objects.using(db_alias).in_bulk(
        {detalle.material_id for detalle in detalles}
    )
    for detalle in detalles:
        material = materiales.get(detalle.material_id)
        if material is None:
            logger.warning(
                "No se pudo revertir stock del pedido %s: no existe el material %s",
                orden.codigo_pedido,
                detalle.material_id,
            )
            continue
        stock_obj, _ = select_for_update_if_supported(
            Stock.objects.using(db_alias), db_alias
        ).get_or_create(
            material=material,
            defaults={"cantidad_actual": 0},
        )
        stock_obj.cantidad_actual = F("cantidad_actual") + detalle.cantidad
        stock_obj.save(using=db_alias)

        MovimientoInventario.objects.using(db_alias).create(
            material=material,
            tipo_movimiento="entrada",
            cantidad=detalle.cantidad,
            observacion=f"{motivo_prefijo} pedido #{orden.codigo_pedido}",
            pedido=orden,
            usuario=usuario,
        )


def liberar_vehiculo_pedido(orden):
    entrega = orden.entregas.first()
    if entrega and entrega.vehiculo:
        vehiculo = entrega.vehiculo
        vehiculo.estado = "disponible"
        vehiculo.save()
        return vehiculo
    return None


def eliminar_pedidos_checkout_incompletos(*, using=None, pedido_id=None, usuario=None):
    """Elimina checkouts pendientes sin pago/proof y devuelve su stock una sola vez."""
    from apps.pagos.models import Pago
    from apps.pedidos.models import Pedido

    db_alias = using or ("remota" if debe_usar_bd_remota() else "default")
    limite = timezone.now() - timedelta(minutes=30)
    pedidos = Pedido.objects.using(db_alias).filter(estado=Pedido.PENDIENTE)
    if pedido_id is not None:
        pedidos = pedidos.filter(codigo_pedido=pedido_id)
    else:
        pedidos = pedidos.filter(fecha_solicitud__lte=limite)

    eliminados = []
    for codigo in list(pedidos.values_list("codigo_pedido", flat=True)):
        try:
            with transaction.atomic(using=db_alias):
                pedido = select_for_update_if_supported(
                    Pedido.objects.using(db_alias), db_alias
                ).filter(codigo_pedido=codigo).first()
                if not pedido or pedido.estado != Pedido.PENDIENTE:
                    continue
                if pedido_id is None and pedido.fecha_solicitud > limite:
                    continue

                pago = Pago.objects.using(db_alias).filter(pedido_id=pedido.pk).first()
                if pago:
                    # Contraentrega no usa archivo. Pagos rechazados conservan su plazo de corrección.
                    if pago.metodo == Pago.METODO_CONTRAENTREGA or pago.estado != Pago.PENDIENTE:
                        continue
                    if not pago.requiere_comprobante():
                        continue
                    if pago.comprobante and pago.comprobante.name:
                        try:
                            if pago.comprobante.storage.exists(pago.comprobante.name):
                                continue
                        except Exception:
                            if pedido_id is None:
                                logger.warning(
                                    "No se pudo comprobar el archivo del pago del pedido #%s; se conserva para reintento.",
                                    pedido.codigo_pedido,
                                )
                                continue

                collector = Collector(using=db_alias)
                collector.collect([pedido])
                revertir_stock_pedido(
                    pedido,
                    usuario,
                    motivo_prefijo="Eliminación automática por pago incompleto",
                    using=db_alias,
                )
                liberar_vehiculo_pedido(pedido)
                pedido.delete(using=db_alias)
                eliminados.append(codigo)
        except ProtectedError:
            logger.warning(
                "No se eliminó el pedido incompleto #%s porque tiene registros financieros protegidos.",
                codigo,
            )
        except Exception:
            logger.exception("No se pudo eliminar el checkout incompleto #%s", codigo)

    return eliminados


def generar_qr_orden(orden):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f"https://tudominio.com/ordenes/{orden.codigo_pedido}/")
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e40af", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=f"qr_orden_{orden.codigo_pedido}.png")
