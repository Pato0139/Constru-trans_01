import logging
import mimetypes
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import router, transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.logistica.models import Entrega
from apps.logistica.services import (
    autorizar_despacho_por_pago,
    cancelar_envio_pedido,
    notificar_evento_logistico,
    validar_integridad_pedido_y_pago_para_despacho,
    verificar_y_cancelar_pedidos_por_vencimiento_correccion_pago,
)
from apps.pagos.forms import PagoFacturaRegistroForm, PagoFacturaRevisionForm
from apps.pagos.models import Factura, Pago, PagoFactura
from apps.pagos.pdf import render_factura_pdf
from apps.pedidos.forms_pagos import PagoRegistroForm, PagoRevisionForm
from apps.pedidos.models import Pedido
from apps.usuarios.views import admin_required
from config.db_utils import select_for_update_if_supported
from config.security import (
    _respuesta_no_autorizada,
    obtener_ip,
    registrar_evento,
    registrar_warning,
    role_required,
)
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
    verificar_y_cancelar_pedidos_por_vencimiento_correccion_pago()
    usuario = _usuario_actual(request)
    query = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()
    metodo = request.GET.get("metodo", "").strip()

    pagos = Pago.objects.select_related(
        "pedido", "pedido__usuario", "pedido__cliente__usuario", "revisado_por"
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
    if estado == Pago.REQUIERE_CORRECCION:
        pagos = pagos.filter(estado=Pago.RECHAZADO).exclude(pedido__estado=Pedido.CANCELADO)
    elif estado:
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
            "estados": Pago.ESTADOS_GESTION,
            "metodos": Pago.METODOS,
        },
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

    verificar_y_cancelar_pedidos_por_vencimiento_correccion_pago(pedido=pedido)
    pedido.refresh_from_db()
    if pedido.estado == Pedido.CANCELADO:
        messages.error(
            request,
            "Este pedido está cancelado (venció el plazo de 12 horas o superó el máximo de intentos de pago). "
            "Debes realizar un nuevo pedido.",
        )
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

    estado_previo = pago.estado if pago else None
    metodo_previo = pago.metodo if pago else ""
    comprobante_previo = pago.comprobante.name if (pago and pago.comprobante) else ""
    observaciones_previas = pago.observaciones if pago else ""
    revisor_previo = pago.revisado_por if pago else None

    if request.method == "POST":
        form = PagoRegistroForm(request.POST, request.FILES, instance=pago)
        if form.is_valid():
            using = router.db_for_write(Pago, instance=pago)
            try:
                with transaction.atomic(using=using):
                    # Bloquear el pedido para evitar condiciones de carrera por envíos repetidos
                    pedido_bloqueado = select_for_update_if_supported(
                        Pedido.objects.using(using), using
                    ).get(pk=pedido.pk)
                    pago_existente = select_for_update_if_supported(
                        Pago.objects.using(using).filter(pedido=pedido_bloqueado), using
                    ).first()

                    if pago_existente and pago_existente.estado == Pago.APROBADO:
                        messages.info(request, "Este pedido ya tiene un pago aprobado.")
                        return redirect("pagos:detalle_pago", pk=pago_existente.pk)

                    era_rechazado = bool(
                        pago_existente
                        and (
                            pago_existente.estado == Pago.RECHAZADO
                            or estado_previo == Pago.RECHAZADO
                            or pago_existente.total_rechazos > 0
                        )
                    )
                    if era_rechazado and pago_existente.detalles.using(using).count() == 0:
                        pago_existente.registrar_intento_historial(
                            estado_intento=Pago.RECHAZADO,
                            metodo=metodo_previo or pago_existente.metodo,
                            comprobante_nombre=comprobante_previo,
                            revisor=revisor_previo or pago_existente.revisado_por,
                            observaciones=observaciones_previas or pago_existente.observaciones,
                            using=using,
                        )

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
                        revisor_adm = getattr(request.user, "usuario", request.user)
                        instancia_pago.marcar_revision(
                            estado=Pago.APROBADO,
                            revisor=revisor_adm,
                            observaciones="Aprobado por administrador al registrar el pago.",
                        )
                        instancia_pago.save(using=using)
                        instancia_pago.registrar_intento_historial(
                            estado_intento=Pago.APROBADO,
                            revisor=revisor_adm,
                            observaciones="Aprobado por administrador al registrar el pago.",
                            using=using,
                        )
                        exigir_det = pedido_bloqueado.detalles.using(using).exists()
                        autorizar_despacho_por_pago(
                            pedido_bloqueado,
                            usuario_admin=revisor_adm,
                            exigir_detalles=exigir_det,
                            using=using,
                        )
                    else:
                        instancia_pago.revisado_por = None
                        instancia_pago.fecha_revision = None
                        instancia_pago.observaciones = ""
                        instancia_pago.save(using=using)
                        instancia_pago.registrar_intento_historial(
                            estado_intento=Pago.PENDIENTE,
                            metodo=instancia_pago.metodo,
                            comprobante_nombre=(
                                instancia_pago.comprobante.name
                                if instancia_pago.comprobante
                                else ""
                            ),
                            observaciones="Comprobante reenviado por cliente"
                            if era_rechazado
                            else "Pago registrado por cliente",
                            using=using,
                        )
                        pedido_bloqueado.save(using=using, update_fields=["estado"])
                        if era_rechazado:
                            notificar_evento_logistico(
                                "comprobante_reenviado",
                                pedido_bloqueado,
                                actor=usuario,
                                using=using,
                            )

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


def _puede_ver_pago_por_id(request, pago_id):
    pago = get_object_or_404(
        Pago.objects.select_related("pedido", "pedido__usuario", "pedido__cliente", "revisado_por"),
        pk=pago_id,
    )
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
    verificar_y_cancelar_pedidos_por_vencimiento_correccion_pago(pedido=pago.pedido)
    pago.pedido.refresh_from_db()
    return render(
        request,
        "pagos/detalle.html",
        {
            "pago": pago,
            "pedido": pago.pedido,
            "historial_intentos": pago.historial_intentos,
        },
    )


@role_required(["admin", "cliente"])
def ver_comprobante_pago(request, pk):
    pago = _puede_ver_pago_por_id(request, pk)
    if pago is None:
        return _respuesta_no_autorizada(request)

    intento_id = request.GET.get("intento", "").strip()
    ruta_archivo = None
    if intento_id and intento_id.isdigit():
        for item in pago.historial_intentos:
            if item["id"] == int(intento_id) and item.get("comprobante"):
                ruta_archivo = item["comprobante"]
                break

    if not ruta_archivo:
        if not pago.comprobante:
            raise Http404("Comprobante no encontrado.")
        ruta_archivo = pago.comprobante.name

    try:
        content_type, _ = mimetypes.guess_type(ruta_archivo)
        descargar = request.GET.get("download") == "1"
        archivo = default_storage.open(ruta_archivo, "rb")
        nombre_descarga = ruta_archivo.split("/")[-1]
        return FileResponse(
            archivo,
            as_attachment=descargar,
            filename=nombre_descarga if descargar else None,
            content_type=content_type or "application/octet-stream",
        )
    except Exception as exc:
        raise Http404("El archivo del comprobante no está disponible.") from exc


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
            return redirect("pagos:detalle_pago", pk=pago.pk)
        accion = form.cleaned_data["accion"]
        observaciones = form.cleaned_data.get("observaciones", "")
        tipo_rechazo = form.cleaned_data.get("tipo_rechazo", "")
        revisor = _revisor_en_base_del_pago(request.user, pago)
        using = pago._state.db or router.db_for_write(Pago, instance=pago)
        try:
            with transaction.atomic(using=using):
                # Bloqueo para evitar doble revisión concurrente.
                pago = select_for_update_if_supported(Pago.objects.using(using), using).get(pk=pago.pk)
                pedido = select_for_update_if_supported(Pedido.objects.using(using), using).get(pk=pago.pedido_id)
                if pago.estado != Pago.PENDIENTE:
                    messages.error(request, "Este pago ya fue revisado y no puede volver a cambiarse.")
                    return redirect("pagos:detalle_pago", pk=pago.pk)
                if accion == "aprobar":
                    validar_integridad_pedido_y_pago_para_despacho(
                        pedido,
                        pago=pago,
                        exigir_detalles=True,
                        using=using,
                    )
                    pago.marcar_revision(
                        estado=Pago.APROBADO,
                        revisor=revisor,
                        observaciones=observaciones,
                    )
                    pago.save(using=using)
                    pago.registrar_intento_historial(
                        estado_intento=Pago.APROBADO,
                        revisor=revisor,
                        observaciones=observaciones or "Pago aprobado",
                        using=using,
                    )
                    autorizar_despacho_por_pago(
                        pedido,
                        usuario_admin=revisor,
                        exigir_detalles=True,
                        using=using,
                    )
                else:
                    if pedido.estado in (Pedido.EN_RUTA, Pedido.ENTREGADO):
                        messages.error(
                            request,
                            "No se puede rechazar el pago de un pedido que ya está en ruta o entregado.",
                        )
                        return redirect("pagos:detalle_pago", pk=pago.pk)
                    etiqueta_tipo = Pago.TIPOS_RECHAZO.get(tipo_rechazo, "")
                    observaciones_finales = observaciones.strip()
                    if etiqueta_tipo and not observaciones_finales.lower().startswith(f"[{etiqueta_tipo.lower()}]"):
                        observaciones_finales = f"[{etiqueta_tipo}] {observaciones_finales}"

                    pago.marcar_revision(
                        estado=Pago.RECHAZADO,
                        revisor=revisor,
                        observaciones=observaciones_finales,
                    )
                    pago.save(using=using)
                    pago.registrar_intento_historial(
                        estado_intento=Pago.RECHAZADO,
                        revisor=revisor,
                        observaciones=observaciones_finales,
                        using=using,
                    )
                    Entrega.objects.using(using).filter(
                        pedido=pedido,
                        estado="pendiente",
                        conductor__isnull=True,
                    ).delete()

                    pedido_cancelado_por_segundo_rechazo = (
                        pago.total_rechazos >= Pago.MAX_RECHAZOS_PERMITIDOS
                    )
                    if pedido_cancelado_por_segundo_rechazo:
                        motivo_auto_segundo = (
                            f"Cancelación automática por segundo rechazo de pago/comprobante "
                            f"({observaciones_finales}). El cliente debe realizar un nuevo pedido."
                        )
                        cancelar_envio_pedido(
                            pedido,
                            revisor,
                            motivo=motivo_auto_segundo,
                            revertir_stock=True,
                            using=using,
                        )
                    else:
                        if pedido.estado in (
                            Pedido.AUTORIZADO_DESPACHO,
                            Pedido.VEHICULO_ASIGNADO,
                        ):
                            pedido.transicionar(Pedido.PENDIENTE)
                            pedido.save(using=using, update_fields=["estado"])
                        notificar_evento_logistico(
                            "pago_rechazado",
                            pedido,
                            actor=revisor,
                            extra_info=observaciones_finales,
                            using=using,
                        )
        except ValidationError as exc:
            for msg in exc.messages:
                messages.error(request, msg)
            return redirect("pagos:detalle_pago", pk=pago.pk)

        if accion == "aprobar":
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
            registrar_actividad(
                request,
                "editar",
                "pagos",
                pago.pk,
                f"Pago del pedido #{pedido.codigo_pedido} rechazado: {pago.observaciones}",
            )
            if pedido.estado == Pedido.CANCELADO:
                messages.error(
                    request,
                    f"Pago rechazado por segunda vez. El pedido #{pedido.codigo_pedido} se canceló automáticamente y pasó al historial.",
                )
            else:
                messages.warning(
                    request,
                    f"Pago rechazado. Se notificó al cliente que tiene 12 horas para corregir su pago o comprobante del pedido #{pedido.codigo_pedido}.",
                )
        return redirect("pagos:detalle_pago", pk=pago.pk)

    return redirect("pagos:detalle_pago", pk=pago.pk)


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
                factura_bloqueada = select_for_update_if_supported(Factura.objects, "default").get(pk=pk)
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
        select_for_update_if_supported(Factura.objects, "default").get(pk=pk)
        pago = select_for_update_if_supported(PagoFactura.objects, "default").get(
            pk=pago_id, factura_id=pk
        )
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
