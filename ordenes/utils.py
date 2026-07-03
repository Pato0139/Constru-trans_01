from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from django.db.models import F

from inventario.models import MovimientoInventario
from usuarios.models import Stock
from core.db_preference import debe_usar_bd_remota


def revertir_stock_pedido(orden, usuario, motivo_prefijo="Cancelación", using=None):
    db_alias = using if using else ("remota" if debe_usar_bd_remota() else "default")
    for detalle in orden.detalles.all():
        stock_obj, _ = (
            Stock.objects.select_for_update()
            .using(db_alias)
            .get_or_create(
                material=detalle.material,
                defaults={"cantidad_actual": 0},
            )
        )
        stock_obj.cantidad_actual = F("cantidad_actual") + detalle.cantidad
        stock_obj.save(using=db_alias)

        MovimientoInventario.objects.create(
            material=detalle.material,
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


def generar_qr_orden(orden):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f"https://tudominio.com/ordenes/{orden.codigo_pedido}/")
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e40af", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=f"qr_orden_{orden.codigo_pedido}.png")
