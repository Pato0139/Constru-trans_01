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


def _estado_archivos_comprobante(pago):
    """Indica si hay una ruta de comprobante registrada y si algún archivo está disponible."""
    almacenamiento = pago._meta.get_field("comprobante").storage
    rutas = []
    if pago.comprobante and pago.comprobante.name:
        rutas.append(pago.comprobante.name)
    for intento in pago.historial_intentos:
        ruta = (intento.get("comprobante") or "").strip()
        if ruta:
            rutas.append(ruta)
    disponibles = False
    for ruta in set(rutas):
        try:
            if almacenamiento.exists(ruta):
                disponibles = True
                break
        except Exception:
            logger.warning("No se pudo verificar la ruta de un comprobante del pago %s", pago.pk, exc_info=True)
    return bool(rutas), disponibles


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

                        if instancia_pago.requiere_comprobante():
                            if not instancia_pago.comprobante or not instancia_pago.comprobante.name:
                                raise ValidationError(
                                    "No se recibió el archivo del comprobante. Selecciónalo nuevamente antes de enviar el pago."
                                )
                            try:
                                archivo_guardado = instancia_pago.comprobante.storage.exists(
                                    instancia_pago.comprobante.name
                                )
                            except Exception as exc:
                                logger.exception(
                                    "No se pudo verificar el comprobante recién guardado del pago %s",
                                    instancia_pago.pk,
                                )
                                raise ValidationError(
                                    "No se pudo verificar el almacenamiento del comprobante. Intenta cargarlo nuevamente."
                                ) from exc
                            if not archivo_guardado:
                                raise ValidationError(
                                    "El comprobante no quedó guardado. Selecciona el archivo nuevamente y vuelve a enviarlo."
                                )

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
            except ValidationError as exc:
                for error in exc.messages:
                    messages.error(request, error)
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
    historial_intentos = pago.historial_intentos
    comprobante_registrado_historial = False
    comprobante_historial = None
    almacenamiento_comprobante = pago._meta.get_field("comprobante").storage
    ultimo_intento_con_comprobante = False
    for intento in reversed(historial_intentos):
        ruta = (intento.get("comprobante") or "").strip()
        intento["comprobante_disponible"] = False
        if not ruta:
            continue
        try:
            intento["comprobante_disponible"] = almacenamiento_comprobante.exists(ruta)
        except Exception:
            logger.warning(
                "No se pudo verificar el comprobante del intento %s del pago %s",
                intento.get("id"),
                pago.pk,
                exc_info=True,
            )
        if not ultimo_intento_con_comprobante:
            ultimo_intento_con_comprobante = True
            comprobante_registrado_historial = True
            if intento["comprobante_disponible"]:
                comprobante_historial = intento
    mostrar_historial_pago = (
        pago.estado == Pago.PENDIENTE
        and (
            pago.metodo == Pago.METODO_CONTRAENTREGA
            or pago.comprobante_existe_en_disco
            or comprobante_historial is not None
        )
    )
    comprobante_registrado, comprobante_disponible = _estado_archivos_comprobante(pago)
    aprobacion_provisional_disponible = (
        pago.estado == Pago.PENDIENTE
        and pago.requiere_comprobante()
        and comprobante_registrado
        and not comprobante_disponible
    )
    usuario_actual = _usuario_actual(request)
    puede_revisar_pago = (
        getattr(usuario_actual, "rol", "") == "admin"
        or bool(getattr(request.user, "is_staff", False))
        or bool(getattr(request.user, "is_superuser", False))
    )
    return render(
        request,
        "pagos/detalle.html",
        {
            "pago": pago,
            "pedido": pago.pedido,
            "historial_intentos": historial_intentos,
            "comprobante_historial": comprobante_historial,
            "comprobante_registrado_historial": comprobante_registrado_historial,
            "mostrar_historial_pago": mostrar_historial_pago,
            "aprobacion_provisional_disponible": aprobacion_provisional_disponible,
            "puede_revisar_pago": puede_revisar_pago,
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
        datos_revision = request.POST.copy()
        aprobacion_provisional = datos_revision.pop("aprobacion_provisional", [""])[0] == "1"
        form = PagoRevisionForm(datos_revision)
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
                    comprobante_registrado, comprobante_disponible = _estado_archivos_comprobante(pago)
                    provisional_aplicable = (
                        pago.requiere_comprobante()
                        and comprobante_registrado
                        and not comprobante_disponible
                    )
                    if aprobacion_provisional and not provisional_aplicable:
                        messages.error(
                            request,
                            "La aprobación provisional solo aplica si hay un comprobante registrado cuyo archivo no está disponible.",
                        )
                        return redirect("pagos:detalle_pago", pk=pago.pk)
                    if provisional_aplicable and not aprobacion_provisional:
                        messages.error(
                            request,
                            "El archivo del comprobante no está disponible. Usa la opción de aprobación provisional para continuar.",
                        )
                        return redirect("pagos:detalle_pago", pk=pago.pk)
                    validar_integridad_pedido_y_pago_para_despacho(
                        pedido,
                        pago=pago,
                        exigir_detalles=True,
                        using=using,
                    )
                    observaciones_revision = observaciones.strip()
                    if aprobacion_provisional:
                        marca_provisional = "[APROBACIÓN PROVISIONAL: COMPROBANTE NO DISPONIBLE]"
                        observaciones_revision = f"{marca_provisional} {observaciones_revision}".strip()[:1000]
                    pago.marcar_revision(
                        estado=Pago.APROBADO,
                        revisor=revisor,
                        observaciones=observaciones_revision,
                    )
                    pago.save(using=using)
                    pago.registrar_intento_historial(
                        estado_intento=Pago.APROBADO,
                        revisor=revisor,
                        observaciones=observaciones_revision or "Pago aprobado",
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
            detalle_aprobacion = (
                "Pago aprobado provisionalmente: comprobante registrado pero archivo no disponible"
                if aprobacion_provisional
                else "Pago del pedido aprobado"
            )
            registrar_actividad(
                request,
                "editar",
                "pagos",
                pago.pk,
                f"{detalle_aprobacion} — pedido #{pedido.codigo_pedido}",
            )
            if aprobacion_provisional:
                messages.warning(
                    request,
                    f"Aprobación provisional registrada. El pedido #{pedido.codigo_pedido} queda autorizado para despacho; el comprobante no pudo verificarse porque su archivo no está disponible.",
                )
            else:
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
