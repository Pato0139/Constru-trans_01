from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.utils import registrar_actividad
from core.security import role_required
from pedidos.models import Pedido
from usuarios.views import admin_required

from .forms import PagoRegistroForm, PagoRevisionForm
from .models import Pago


def _usuario_actual(request):
    return getattr(request.user, "usuario", request.user)


def _cliente_es_dueno(usuario, pedido):
    if pedido.usuario_id == usuario.pk:
        return True
    return bool(pedido.cliente_id and pedido.cliente.usuario_id == usuario.pk)


@role_required(["admin", "cliente"])
def lista_pagos(request):
    usuario = _usuario_actual(request)
    pagos = (
        Pago.objects.select_related("pedido", "pedido__usuario", "pedido__cliente", "revisado_por")
        .order_by("-fecha_registro")
    )
    if getattr(usuario, "rol", "") == "cliente":
        pagos = pagos.filter(Q(pedido__usuario=usuario) | Q(pedido__cliente__usuario=usuario))
    estado = request.GET.get("estado", "").strip()
    if estado:
        pagos = pagos.filter(estado=estado)
    return render(
        request,
        "pagos/lista.html",
        {"pagos": pagos, "estado_actual": estado},
    )


@role_required(["cliente"])
def registrar_pago(request, pedido_id):
    usuario = _usuario_actual(request)
    pedido = get_object_or_404(Pedido, codigo_pedido=pedido_id)

    if not _cliente_es_dueno(usuario, pedido):
        messages.error(request, "No puedes registrar el pago de un pedido ajeno.")
        return redirect("clientes:mis_pedidos")

    if pedido.estado == Pedido.CANCELADO:
        messages.error(request, "Este pedido está cancelado.")
        return redirect("clientes:mis_pedidos")

    pago = pedido.pago_actual
    if pago and pago.estado == Pago.APROBADO:
        messages.info(request, "Este pedido ya tiene un pago aprobado.")
        return redirect("pagos:detalle_pago", pk=pago.pk)

    if request.method == "POST":
        form = PagoRegistroForm(request.POST, request.FILES, instance=pago)
        if form.is_valid():
            with transaction.atomic():
                pago = form.save(commit=False)
                pago.pedido = pedido
                pago.estado = Pago.PENDIENTE
                pago.revisado_por = None
                pago.fecha_revision = None
                pago.observaciones = ""
                if not pago.monto:
                    pago.monto = pedido.total or pedido.precio or 0
                pago.save()
                registrar_actividad(
                    request,
                    "crear",
                    "pagos",
                    pago.pk,
                    f"Cliente registró pago del pedido #{pedido.codigo_pedido}",
                )
            messages.success(request, "Pago registrado. Queda pendiente de revisión.")
            return redirect("pagos:detalle_pago", pk=pago.pk)
    else:
        form = PagoRegistroForm(
            instance=pago,
            initial={"monto": pedido.total or pedido.precio or 0},
        )

    return render(
        request,
        "pagos/registrar.html",
        {"form": form, "pedido": pedido, "pago": pago},
    )


def _puede_ver_pago(usuario, pago):
    rol = getattr(usuario, "rol", "")
    if rol == "admin" or getattr(usuario, "is_superuser", False):
        return True
    if rol == "cliente":
        return _cliente_es_dueno(usuario, pago.pedido)
    return False


@role_required(["admin", "cliente"])
def detalle_pago(request, pk):
    pago = get_object_or_404(
        Pago.objects.select_related("pedido", "pedido__usuario", "pedido__cliente", "revisado_por"),
        pk=pk,
    )
    usuario = _usuario_actual(request)
    if not _puede_ver_pago(usuario, pago):
        messages.error(request, "No tienes permiso para ver este pago.")
        if getattr(usuario, "rol", "") == "cliente":
            return redirect("clientes:mis_pedidos")
        return redirect("pagos:lista_pagos")
    return render(request, "pagos/detalle.html", {"pago": pago, "pedido": pago.pedido})


@admin_required
def revisar_pago(request, pk):
    pago = get_object_or_404(
        Pago.objects.select_related("pedido"),
        pk=pk,
    )
    pedido = pago.pedido

    if request.method == "POST":
        form = PagoRevisionForm(request.POST)
        accion = request.POST.get("accion")
        if form.is_valid() and accion in ("aprobar", "rechazar"):
            observaciones = form.cleaned_data.get("observaciones", "")
            if accion == "rechazar" and not observaciones.strip():
                messages.error(request, "Indica el motivo del rechazo.")
                return render(
                    request,
                    "pagos/revisar.html",
                    {"form": form, "pago": pago, "pedido": pedido},
                )
            with transaction.atomic():
                if accion == "aprobar":
                    pago.marcar_revision(
                        estado=Pago.APROBADO,
                        revisor=request.user,
                        observaciones=observaciones,
                    )
                    pago.save()
                    if pedido.estado == Pedido.PENDIENTE:
                        pedido.estado = Pedido.AUTORIZADO_DESPACHO
                        pedido.save(update_fields=["estado"])
                    registrar_actividad(
                        request,
                        "editar",
                        "pagos",
                        pago.pk,
                        f"Pago del pedido #{pedido.codigo_pedido} aprobado",
                    )
                    messages.success(
                        request,
                        f"Pago aprobado. El pedido #{pedido.codigo_pedido} queda autorizado para despacho.",
                    )
                else:
                    if pedido.estado in (Pedido.EN_RUTA, Pedido.ENTREGADO):
                        messages.error(
                            request,
                            "No se puede rechazar el pago de un pedido que ya está en ruta o entregado.",
                        )
                        return redirect("pagos:detalle_pago", pk=pago.pk)
                    pago.marcar_revision(
                        estado=Pago.RECHAZADO,
                        revisor=request.user,
                        observaciones=observaciones,
                    )
                    pago.save()
                    if pedido.estado in (
                        Pedido.AUTORIZADO_DESPACHO,
                        Pedido.VEHICULO_ASIGNADO,
                    ):
                        pedido.estado = Pedido.PENDIENTE
                        pedido.save(update_fields=["estado"])
                    registrar_actividad(
                        request,
                        "editar",
                        "pagos",
                        pago.pk,
                        f"Pago del pedido #{pedido.codigo_pedido} rechazado",
                    )
                    messages.warning(
                        request,
                        f"Pago rechazado. El pedido #{pedido.codigo_pedido} no avanza a despacho.",
                    )
            return redirect("pagos:detalle_pago", pk=pago.pk)
    else:
        form = PagoRevisionForm(initial={"observaciones": pago.observaciones})

    return render(
        request,
        "pagos/revisar.html",
        {"form": form, "pago": pago, "pedido": pedido},
    )
