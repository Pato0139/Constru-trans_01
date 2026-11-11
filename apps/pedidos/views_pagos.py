from django.db.models import Q
from django.shortcuts import render

from apps.pagos.models import Factura, PagoFactura
from apps.pagos.views import (  # noqa: F401
    _cliente_es_dueno,
    _monto_pedido,
    _puede_ver_pago,
    _revisor_en_base_del_pago,
    _usuario_actual,
    descargar_factura_pedido,
    descargar_pdf,
    detalle_factura,
    detalle_pago,
    lista_pagos,
    mis_facturas,
    mis_pagos,
    registrar_pago,
    registrar_pago_pedido,
    revisar_pago,
    revisar_pago_pedido,
    ver_comprobante_pago,
)
from apps.usuarios.views import admin_required


@admin_required
def lista_facturas(request):
    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    qs = Factura.objects.select_related("pedido", "cliente__usuario")
    if q:
        qs = qs.filter(
            Q(numero__icontains=q)
            | Q(pedido__codigo_pedido__icontains=q)
            | Q(cliente__usuario__nombres__icontains=q)
            | Q(cliente__usuario__apellidos__icontains=q)
        )
    if estado:
        qs = qs.filter(estado=estado)
    return render(
        request,
        "pagos/facturas_lista.html",
        {
            "facturas": qs,
            "estados": Factura.Estado.choices,
            "q": q,
            "estado_actual": estado,
        },
    )


@admin_required
def gestion_pagos(request):
    pagos = PagoFactura.objects.select_related(
        "factura__pedido", "factura__cliente__usuario", "revisado_por"
    ).order_by("-fecha_registro")
    estado = request.GET.get("estado", "").strip()
    if estado:
        pagos = pagos.filter(estado=estado)
    return render(
        request,
        "pagos/gestion_pagos.html",
        {"pagos": pagos, "estado_actual": estado},
    )


@admin_required
def historial_pagos(request):
    pagos = (
        PagoFactura.objects.select_related("factura")
        .filter(estado=PagoFactura.Estado.APROBADO)
        .order_by("-fecha_revision")
    )
    return render(request, "pagos/historial_pagos.html", {"pagos": pagos})


