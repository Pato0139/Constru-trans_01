from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from usuarios.views import admin_required

from .models import Pago


@admin_required
def lista_pagos(request):
    query = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    metodo = request.GET.get("metodo", "").strip()

    pagos = Pago.objects.select_related("pedido", "pedido__cliente", "pedido__usuario")
    if query:
        pagos = pagos.filter(
            Q(id__icontains=query)
            | Q(pedido__codigo_pedido__icontains=query)
            | Q(referencia__icontains=query)
            | Q(pedido__cliente__nombres__icontains=query)
            | Q(pedido__cliente__apellidos__icontains=query)
            | Q(pedido__usuario__nombres__icontains=query)
            | Q(pedido__usuario__apellidos__icontains=query)
        )
    if estado:
        pagos = pagos.filter(estado=estado)
    if metodo:
        pagos = pagos.filter(metodo=metodo)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(
            request,
            "pagos/_tabla_body.html",
            {"pagos": pagos},
        )

    return render(
        request,
        "pagos/lista.html",
        {
            "pagos": pagos,
            "query": query,
            "estado_actual": estado,
            "metodo_actual": metodo,
            "estados": Pago.ESTADOS,
            "metodos": Pago.METODOS,
        },
    )


@admin_required
def _cambiar_estado(request, pk, estado, mensaje):
    if request.method != "POST":
        messages.error(request, "La acción solicitada no es válida.")
        return redirect("pagos:lista_pagos")

    pago = get_object_or_404(Pago, pk=pk)
    if pago.estado != Pago.ESTADOS[0][0]:
        messages.info(request, "Este pago ya fue procesado.")
        return redirect("pagos:lista_pagos")

    pago.estado = estado
    pago.save(update_fields=["estado", "fecha_actualizacion"])
    messages.success(request, mensaje)
    return redirect("pagos:lista_pagos")


@admin_required
def aprobar_pago(request, pk):
    return _cambiar_estado(request, pk, "aprobado", "Pago aprobado correctamente.")


@admin_required
def rechazar_pago(request, pk):
    return _cambiar_estado(request, pk, "rechazado", "Pago rechazado correctamente.")
