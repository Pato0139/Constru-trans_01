from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods

from config.utils import registrar_actividad
from config.security import (role_required, _respuesta_no_autorizada,
                             obtener_ip, registrar_evento, registrar_warning)
from apps.usuarios.views import admin_required

from .models import Factura, PagoFactura
from .forms import PagoFacturaRegistroForm, PagoFacturaRevisionForm
from .pdf import render_factura_pdf
from apps.pagos.models import Factura, Pago, PagoFactura
from apps.pagos.pdf import render_factura_pdf
from apps.pedidos.forms_pagos import PagoRegistroForm, PagoRevisionForm
from apps.pedidos.models import Pedido
from apps.usuarios.views import admin_required
from config.security import (
    _respuesta_no_autorizada,
    obtener_ip,
    registrar_evento,
    registrar_warning,
    role_required,
)
from config.utils import registrar_actividad


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
        return sum(
            (
                Decimal(detalle.cantidad) * detalle.precio_unitario
                for detalle in pedido.detalles.all()
            ),
            Decimal("0"),
        )

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
        {
            "pagos": pagos,
            "estado_actual": estado,
            "metodo_actual": metodo,
            "query_actual": query,
            "estados": Pago.ESTADOS,
            "metodos": Pago.METODOS,
        },
    )


@role_required(["cliente"])
def registrar_pago_pedido(request, pedido_id):
    usuario = _usuario_actual(request)
    pedido = get_object_or_404(Pedido, codigo_pedido=pedido_id)

    if not _cliente_es_dueno(usuario, pedido):
        messages.error(request, "No puedes registrar el pago de un pedido ajeno.")
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
    pedido.total = monto_pedido

    pago = pedido.pago_actual
    if pago and pago.estado == Pago.APROBADO:
        messages.info(request, "Este pedido ya tiene un pago aprobado.")
        return redirect("pagos:detalle_pago", pk=pago.pk)

    if request.method == "POST":
        form = PagoRegistroForm(request.POST, request.FILES, instance=pago)
        if form.is_valid():
            with transaction.atomic():
                if pago and pago.pk:
                    bloqueado = Pago.objects.select_for_update().get(pk=pago.pk)
                    if bloqueado.estado == Pago.APROBADO:
                        messages.info(request, "Este pedido ya tiene un pago aprobado.")
                        return redirect("pagos:detalle_pago", pk=pago.pk)
                pago = form.save(commit=False)
                pago.pedido = pedido
                pago.transicionar(Pago.PENDIENTE)  # rechazado -> pendiente
                pago.revisado_por = None
                pago.fecha_revision = None
                pago.observaciones = ""
                pago.monto = monto_pedido  # el monto lo fija el servidor, nunca el cliente
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


def _puede_ver_pago_por_id(request, pago_id):
    pago = get_object_or_404(Pago, pk=pago_id)
    usuario = _usuario_actual(request)
    if not _puede_ver_pago(usuario, pago):
        ip = obtener_ip(request)
        registrar_warning(ip)
        registrar_evento(
            request,
            "role_violation",
            gravedad="high",
            detalles={"causa": "ver_pago_ajeno", "pago_id": pago.pk},
        )
        return None
    return pago


@role_required(["admin", "cliente"])
def detalle_pago(request, pk):
    pago = _puede_ver_pago_por_id(request, pk)
    if pago is None:
        return _respuesta_no_autorizada(request)
    return render(request, "pagos/detalle.html", {"pago": pago, "pedido": pago.pedido})


@admin_required
@require_http_methods(["GET", "POST"])
def revisar_pago_pedido(request, pk):
    pago = get_object_or_404(
        Pago.objects.select_related("pedido"),
        pk=pk,
    )
    pedido = pago.pedido

    if request.method == "POST":
        form = PagoRevisionForm(request.POST)
        if pago.estado != Pago.PENDIENTE:
            messages.error(request, "Este pago ya fue revisado y no puede volver a cambiarse.")
            return redirect("pagos:detalle_pago", pk=pago.pk)
        if not form.is_valid():
            for errores in form.errors.values():
                for e in errores:
                    messages.error(request, e)
            return render(
                request,
                "pagos/revisar.html",
                {"form": form, "pago": pago, "pedido": pedido},
            )
        accion = form.cleaned_data["accion"]
        observaciones = form.cleaned_data.get("observaciones", "")
        revisor = _revisor_en_base_del_pago(request.user, pago)
        with transaction.atomic():
            # Bloqueo para evitar doble revisión concurrente.
            pago = Pago.objects.select_for_update().get(pk=pago.pk)
            pedido = Pedido.objects.select_for_update().get(pk=pago.pedido_id)
            if pago.estado != Pago.PENDIENTE:
                messages.error(request, "Este pago ya fue revisado y no puede volver a cambiarse.")
                return redirect("pagos:detalle_pago", pk=pago.pk)
            if accion == "aprobar":
                pago.marcar_revision(
                    estado=Pago.APROBADO,
                    revisor=revisor,
                    observaciones=observaciones,
                )
                pago.save()
                if pedido.estado == Pedido.PENDIENTE:
                    pedido.transicionar(Pedido.AUTORIZADO_DESPACHO)
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
                    pedido.transicionar(Pedido.PENDIENTE)
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
@require_http_methods(["GET", "POST"])
def registrar_pago(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    if request.method == "POST":
        form = PagoFacturaRegistroForm(request.POST, request.FILES, factura=factura)
        if form.is_valid():
            with transaction.atomic():
                factura_bloqueada = Factura.objects.select_for_update().get(pk=pk)
                pago = form.save(commit=False)
                if pago.monto > factura_bloqueada.saldo_pendiente:
                    form.add_error("monto", "El saldo de la factura cambió; verifica el monto.")
                else:
                    pago.factura = factura_bloqueada
                    pago.registrado_por = request.user
                    pago.save()
                    registrar_actividad(
                        request,
                        "crear",
                        "pagos",
                        pago.pk,
                        f"Pago registrado a factura {factura.numero}",
                    )
                    messages.success(request, "Pago registrado y pendiente de revisión.")
                    return redirect("pagos:detalle_factura", pk=pk)
    else:
        form = PagoFacturaRegistroForm(
            factura=factura,
            initial={"monto": factura.saldo_pendiente},
        )

    return render(
        request,
        "pagos/facturas_registrar_pago.html",
        {
            "factura": factura,
            "saldo_pendiente": factura.saldo_pendiente,
            "metodos": PagoFactura.Metodo.choices,
            "form": form,
        },
    )


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
        PagoFactura.objects.select_related("factura__pedido")
        .filter(factura__cliente__usuario=usuario)
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
    usuario = _usuario_actual(request)
    if getattr(usuario, "rol", "") == "cliente" and factura.cliente.usuario_id != usuario.pk:
        raise Http404()
    pdf_bytes = render_factura_pdf(factura)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{factura.numero}.pdf"'
    return response


@role_required(["admin", "cliente"])
def descargar_factura_pedido(request, pedido_id):
    factura = get_object_or_404(Factura, pedido_id=pedido_id)
    return descargar_pdf(request, factura.pk)


@admin_required
@require_POST
def revisar_pago(request, pk, pago_id):
    pago = get_object_or_404(PagoFactura, pk=pago_id, factura_id=pk)
    form = PagoFacturaRevisionForm(request.POST)
    if not form.is_valid():
        for errores in form.errors.values():
            for e in errores:
                messages.error(request, e)
        return render(request, "pagos/revisar_pago_factura.html", {"pago": pago, "form": form})

    accion = form.cleaned_data["accion"]
    with transaction.atomic():
        Factura.objects.select_for_update().get(pk=pk)
        pago = PagoFactura.objects.select_for_update().get(pk=pago_id, factura_id=pk)
        if pago.estado != PagoFactura.Estado.PENDIENTE:
            messages.error(request, "Este pago ya fue revisado.")
        if accion == "aprobar" and pago.monto > pago.factura.saldo_pendiente:
            messages.error(request, "El pago supera el saldo pendiente de la factura.")
            return redirect("pagos:detalle_factura", pk=pk)
        pago.transicionar(
            PagoFactura.Estado.APROBADO if accion == "aprobar" else PagoFactura.Estado.RECHAZADO
        )
        pago.revisado_por = request.user
        pago.fecha_revision = timezone.now()
        pago.observaciones = form.cleaned_data.get("observaciones", "")
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
    return redirect("pagos:lista_pagos")
