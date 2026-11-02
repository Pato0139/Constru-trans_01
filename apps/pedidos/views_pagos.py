import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import router, transaction
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.pagos.models import Factura, Pago, PagoFactura
from apps.pagos.pdf import render_factura_pdf
from apps.pedidos.forms_pagos import PagoRegistroForm, PagoRevisionForm
from apps.pedidos.models import Pedido
from apps.usuarios.views import admin_required
from config.db_utils import select_for_update_if_supported
from config.security import role_required
from config.utils import registrar_actividad

logger = logging.getLogger(__name__)


def _usuario_actual(request):
    return getattr(request.user, "usuario", request.user)


def _revisor_en_base_del_pago(usuario, pago):
    using = pago._state.db
    if usuario._state.db == using:
        return usuario
    return get_user_model().objects.using(using).filter(username=usuario.get_username()).first()


def _cliente_es_dueno(usuario, pedido):
    if pedido.usuario_id == usuario.pk:
        return True
    return bool(pedido.cliente_id and pedido.cliente.usuario_id == usuario.pk)


def _monto_pedido(pedido):
    if pedido.detalles.exists():
        return sum((detalle.subtotal for detalle in pedido.detalles.all()), Decimal("0"))

    return pedido.total or pedido.precio or Decimal("0")


@role_required(["admin", "cliente"])
def lista_pagos(request):
    usuario = _usuario_actual(request)
    query = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    metodo = request.GET.get("metodo", "").strip()

    pagos = Pago.objects.select_related(
        "pedido", "pedido__usuario", "pedido__cliente", "revisado_por"
    ).order_by("-fecha_registro")

    if getattr(usuario, "rol", "") == "cliente":
        pagos = pagos.filter(Q(pedido__usuario=usuario) | Q(pedido__cliente__usuario=usuario))

    if query:
        pagos = pagos.filter(
            Q(id__icontains=query)
            | Q(pedido__codigo_pedido__icontains=query)
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
        {"pagos": pagos, "estado_actual": estado, "metodo_actual": metodo, "query_actual": query},
    )


@role_required(["admin", "cliente"])
def registrar_pago_pedido(request, pedido_id):
    usuario = _usuario_actual(request)
    pedido = get_object_or_404(Pedido, codigo_pedido=pedido_id)

    es_admin = getattr(usuario, "rol", "") == "admin"
    if not (es_admin or _cliente_es_dueno(usuario, pedido)):
        messages.error(request, "No puedes registrar el pago de un pedido ajeno.")
        if es_admin:
            return redirect("pedidos:ver_pedido_admin", id=pedido.codigo_pedido)
        return redirect("clientes:mis_pedidos")

    if pedido.estado == Pedido.CANCELADO:
        messages.error(request, "Este pedido está cancelado.")
        return redirect("clientes:mis_pedidos")

    monto_pedido = _monto_pedido(pedido)
    if monto_pedido <= 0:
        messages.error(
            request,
            "No se puede registrar el pago porque el pedido no tiene un valor válido. "
            "Revisa los materiales y sus precios antes de continuar.",
        )
        return redirect("clientes:mis_pedidos")

    pago = pedido.pago_actual
    if pago and pago.estado == Pago.APROBADO:
        messages.info(request, "Este pedido ya tiene un pago aprobado.")
        return redirect("pagos:detalle_pago", pk=pago.pk)

    if request.method == "POST":
        form = PagoRegistroForm(request.POST, request.FILES, instance=pago)
        if form.is_valid():
            using = router.db_for_write(Pago, instance=pago)
            try:
                with transaction.atomic(using=using):
                    pedido_bloqueado = select_for_update_if_supported(
                        Pedido.objects.using(using), using
                    ).get(pk=pedido.pk)
                    pago_existente = select_for_update_if_supported(
                        Pago.objects.using(using).filter(pedido=pedido_bloqueado), using
                    ).first()

                    if pago_existente and pago_existente.estado == Pago.APROBADO:
                        messages.info(request, "Este pedido ya tiene un pago aprobado.")
                        return redirect("pagos:detalle_pago", pk=pago_existente.pk)

                    if pago_existente:
                        instancia_pago = pago_existente
                        instancia_pago.metodo = form.cleaned_data["metodo"]
                        if form.cleaned_data.get("comprobante"):
                            instancia_pago.comprobante = form.cleaned_data["comprobante"]
                    else:
                        instancia_pago = form.save(commit=False)
                        instancia_pago.pedido = pedido_bloqueado

                    instancia_pago.transicionar(Pago.PENDIENTE)
                    instancia_pago.monto = monto_pedido
                    if es_admin:
                        instancia_pago.marcar_revision(
                            estado=Pago.APROBADO,
                            revisor=getattr(request.user, "usuario", request.user),
                            observaciones="Aprobado por administrador al registrar el pago.",
                        )
                        if pedido_bloqueado.estado == Pedido.PENDIENTE:
                            pedido_bloqueado.transicionar(Pedido.AUTORIZADO_DESPACHO)
                    else:
                        instancia_pago.revisado_por = None
                        instancia_pago.fecha_revision = None
                        instancia_pago.observaciones = ""
                    instancia_pago.save(using=using)
                    pedido_bloqueado.save(using=using, update_fields=["estado"])

                try:
                    registrar_actividad(
                        request,
                        "crear",
                        "pagos",
                        instancia_pago.pk,
                        f"{'Administrador' if es_admin else 'Cliente'} registró y {'aprobó' if es_admin else 'envió'} pago del pedido #{pedido.codigo_pedido}",
                    )
                except Exception:
                    logger.warning(
                        "No fue posible registrar la actividad del pago %s del pedido %s",
                        getattr(instancia_pago, "pk", None),
                        pedido.codigo_pedido,
                        exc_info=True,
                    )

                if es_admin:
                    messages.success(
                        request,
                        "Pago registrado y aprobado automáticamente. El pedido queda autorizado para despacho.",
                    )
                else:
                    messages.success(request, "Pago registrado. Queda pendiente de revisión.")
                return redirect("pagos:detalle_pago", pk=instancia_pago.pk)
            except Exception as exc:
                logger.exception(
                    "Error al registrar pago del pedido #%s: %s", pedido.codigo_pedido, exc
                )
                messages.error(
                    request,
                    "Ocurrió un error al procesar el registro del pago. "
                    "Por favor intenta nuevamente o contacta a soporte.",
                )
    else:
        form = PagoRegistroForm(
            instance=pago,
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
def revisar_pago_pedido(request, pk):
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
            revisor = _revisor_en_base_del_pago(request.user, pago)
            with transaction.atomic():
                if accion == "aprobar":
                    pago.marcar_revision(
                        estado=Pago.APROBADO,
                        revisor=revisor,
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
                        revisor=revisor,
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


# ======================
# Consolidado desde la app de facturacion (ahora dentro de pagos)
# ======================


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
def registrar_pago(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    if request.method == "POST":
        try:
            monto_raw = request.POST.get("monto", "0").replace(",", ".")
            monto = float(monto_raw)
        except ValueError:
            monto = 0
        saldo = factura.saldo_pendiente
        if monto <= 0 or monto > saldo + 0.001:
            messages.error(request, "Monto inválido o superior al saldo pendiente.")
            return redirect("pagos:registrar_pago", pk=pk)

        with transaction.atomic():
            pago = PagoFactura.objects.create(
                factura=factura,
                monto=monto,
                metodo=request.POST.get("metodo", PagoFactura.Metodo.EFECTIVO),
                referencia=request.POST.get("referencia", "").strip(),
                evidencia=request.FILES.get("evidencia"),
                registrado_por=request.user,
            )
            registrar_actividad(
                request,
                "crear",
                "pagos",
                pago.pk,
                f"Pago registrado a factura {factura.numero}",
            )
        messages.success(request, "Pago registrado y pendiente de revisión.")
        return redirect("pagos:detalle_factura", pk=pk)

    return render(
        request,
        "pagos/facturas_registrar_pago.html",
        {
            "factura": factura,
            "saldo_pendiente": factura.saldo_pendiente,
            "metodos": PagoFactura.Metodo.choices,
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


@role_required(["cliente"])
def mis_facturas(request):
    usuario = _usuario_actual(request)
    facturas = (
        Factura.objects.select_related("pedido")
        .filter(cliente__usuario=usuario)
        .order_by("-fecha_emision")
    )
    return render(request, "pagos/mis_facturas.html", {"facturas": facturas})


@role_required(["cliente"])
def mis_pagos(request):
    usuario = _usuario_actual(request)
    pagos = (
        Pago.objects.select_related("pedido", "pedido__usuario", "pedido__cliente")
        .filter(Q(pedido__usuario=usuario) | Q(pedido__cliente__usuario=usuario))
        .order_by("-fecha_registro")
    )
    return render(request, "pagos/mis_pagos.html", {"pagos": pagos})


@role_required(["admin", "cliente"])
def detalle_factura(request, pk):
    factura = get_object_or_404(Factura.objects.select_related("pedido", "cliente__usuario"), pk=pk)
    usuario = _usuario_actual(request)
    es_cliente = getattr(usuario, "rol", "") == "cliente"
    if es_cliente and factura.cliente.usuario_id != usuario.pk:
        raise Http404()
    return render(
        request,
        "pagos/factura_detalle.html",
        {
            "factura": factura,
            "pagos": factura.pagos_factura.all(),
            "saldo_pendiente": factura.saldo_pendiente,
        },
    )


@role_required(["admin", "cliente"])
def descargar_pdf(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    pdf_bytes = render_factura_pdf(factura)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{factura.numero}.pdf"'
    return response


@role_required(["admin", "cliente"])
def descargar_factura_pedido(request, pedido_id):
    factura = get_object_or_404(Factura, pedido_id=pedido_id)
    return descargar_pdf(request, factura.pk)


@admin_required
def revisar_pago(request, pk, pago_id):
    pago = get_object_or_404(PagoFactura, pk=pago_id, factura_id=pk)
    accion = request.POST.get("accion")
    if request.method == "POST" and accion in ("aprobar", "rechazar"):
        pago.estado = (
            PagoFactura.Estado.APROBADO if accion == "aprobar" else PagoFactura.Estado.RECHAZADO
        )
        pago.revisado_por = request.user
        pago.fecha_revision = timezone.now()
        pago.observaciones = request.POST.get("observaciones", "")
        pago.save()
        if accion == "aprobar":
            pago.factura.recalcular_estado()
        registrar_actividad(
            request,
            "editar",
            "pagos",
            pago.pk,
            f"Pago {pago.pk} {pago.estado} — factura {pago.factura.numero}",
        )
        messages.success(request, f"Pago {pago.estado}.")
        return redirect("pagos:gestion_pagos")
    return render(request, "pagos/revisar_pago_factura.html", {"pago": pago})
