import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import F, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.catalogo.models import MaterialConstruccion, Stock
from apps.catalogo.models.movimientos import MovimientoInventario
from apps.logistica.models import ConductorVehiculo, Entrega, Novedad, Vehiculo
from apps.logistica.services import (
    asignar_conductor_y_vehiculo,
    autorizar_despacho_por_pago,
    cancelar_envio_pedido,
    confirmar_preparacion_e_iniciar_ruta,
    marcar_pedido_entregado,
    verificar_y_cancelar_pedidos_por_vencimiento_correccion_pago,
)
from apps.usuarios.models import Conductor, Usuario
from apps.usuarios.views import admin_required
from config.db_preference import debe_usar_bd_remota
from config.db_utils import select_for_update_if_supported
from config.errors import formatear_errores
from config.security import (
    _respuesta_no_autorizada,
    obtener_ip,
    registrar_evento,
    registrar_warning,
    role_required,
)
from config.utils import registrar_actividad

from .forms import AgregarMaterialForm, CambioEstadoPedidoForm, FiltroPedidosForm
from .models import DetallePedido, DetalleSolicitudPedido, Pedido, SolicitudPedido
from .utils import liberar_vehiculo_pedido, revertir_stock_pedido


def _mensajes_error(request, origen):
    for d in formatear_errores(origen):
        messages.error(request, d["mensaje"])

logger = logging.getLogger(__name__)


@admin_required
def calcular_total(request, id):
    orden = get_object_or_404(Pedido, codigo_pedido=id)
    total = orden.calcular_total()
    return JsonResponse({"total": float(total)})


@admin_required
@require_POST
def eliminar_detalle(request, id):
    detalle = get_object_or_404(DetallePedido, id_detalle_pedido=id)
    orden = detalle.pedido
    if orden.estado != Pedido.PENDIENTE:
        messages.error(request, "Solo se pueden modificar pedidos pendientes.")
        return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)
    db_alias = "remota" if debe_usar_bd_remota() else "default"

    with transaction.atomic():
        with transaction.atomic(using=db_alias):
            stock_obj = select_for_update_if_supported(Stock.objects.using(db_alias), db_alias).get(
                material=detalle.material
            )
            stock_obj.cantidad_actual = F("cantidad_actual") + detalle.cantidad
            stock_obj.save(using=db_alias)

        MovimientoInventario.objects.create(
            material=detalle.material,
            tipo_movimiento="entrada",
            cantidad=detalle.cantidad,
            observacion=f"Eliminación detalle pedido #{orden.codigo_pedido}",
            pedido=orden,
            usuario=request.user,
        )

        detalle.delete()
        orden.calcular_total()

    messages.success(request, "Material eliminado de la orden.")
    return redirect("pedidos:agregar_materiales", id=orden.codigo_pedido)


@admin_required
def agregar_materiales(request, id):
    orden = get_object_or_404(Pedido, codigo_pedido=id)
    if orden.estado != Pedido.PENDIENTE:
        messages.error(request, "Solo se pueden modificar pedidos pendientes.")
        return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)
    materiales = MaterialConstruccion.objects.all()
    detalles = orden.detalles.all()

    if request.method == "POST":
        form = AgregarMaterialForm(request.POST)
        if not form.is_valid():
            _mensajes_error(request, form.errors)
            return redirect("pedidos:agregar_materiales", id=orden.codigo_pedido)
        cantidad = form.cleaned_data["cantidad"]
        material = get_object_or_404(MaterialConstruccion, pk=form.cleaned_data["material"])

        with transaction.atomic():
            orden = Pedido.objects.select_for_update().get(pk=orden.pk)
            if orden.estado != Pedido.PENDIENTE:
                messages.error(request, "Solo se pueden modificar pedidos pendientes.")
                return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)
            stock_obj = Stock.objects.select_for_update().get(material=material)
            if stock_obj.cantidad_actual < cantidad:
                messages.error(request, "Stock insuficiente")
                return redirect("pedidos:agregar_materiales", id=orden.codigo_pedido)

            detalle, created = DetallePedido.objects.get_or_create(
                pedido=orden,
                material=material,
                defaults={
                    "cantidad": cantidad,
                    "precio_unitario": material.precio_referencia,
                },
            )
            if not created:
                detalle.cantidad += cantidad
                detalle.full_clean(exclude=["pedido", "material"])
                detalle.save()

            stock_obj.cantidad_actual = F("cantidad_actual") - cantidad
            stock_obj.save()

            MovimientoInventario.objects.create(
                material=material,
                tipo_movimiento="salida",
                cantidad=cantidad,
                observacion=f"Agregado a pedido #{orden.codigo_pedido}",
                pedido=orden,
                usuario=request.user,
            )

            orden.calcular_total()
            messages.success(request, f"Se agregaron {cantidad} de {material.nombre}")

        return redirect("pedidos:agregar_materiales", id=orden.codigo_pedido)

    context = {"orden": orden, "materiales": materiales, "detalles": detalles}
    return render(request, "pedidos/agregar_materiales.html", context)


def buscar_pedidos_admin(cliente_query=None, fecha_query=None, q=None, estado=None):
    pedidos = (
        Pedido.objects.all()
        .select_related("usuario", "cliente__usuario", "conductor__usuario", "pago")
        .prefetch_related(
            "detalles__material",
            "entregas__conductor__usuario",
            "entregas__vehiculo",
            "entregas__confirmado_salida_por",
            "entregas__entregado_por",
        )
        .order_by("-fecha_solicitud")
    )

    if cliente_query:
        pedidos = pedidos.filter(
            Q(cliente__nombres__icontains=cliente_query)
            | Q(cliente__apellidos__icontains=cliente_query)
            | Q(usuario__nombres__icontains=cliente_query)
            | Q(usuario__apellidos__icontains=cliente_query)
        )

    if fecha_query:
        pedidos = pedidos.filter(fecha_solicitud__date=fecha_query)

    if q:
        pedidos = pedidos.filter(
            Q(codigo_pedido__icontains=q)
            | Q(direccion_destino__icontains=q)
            | Q(cliente__nombres__icontains=q)
            | Q(cliente__apellidos__icontains=q)
            | Q(usuario__nombres__icontains=q)
            | Q(usuario__apellidos__icontains=q)
        )

    if estado:
        pedidos = pedidos.filter(estado=estado)

    return pedidos


@admin_required
def _render_lista_por_estado(
    request,
    estado,
    titulo,
    *,
    solo_autorizados_despacho=False,
    es_historial=False,
):
    from apps.pagos.models import Pago

    verificar_y_cancelar_pedidos_por_vencimiento_correccion_pago()

    filtro = FiltroPedidosForm(request.GET)
    if filtro.is_valid():
        datos = filtro.cleaned_data
    else:
        _mensajes_error(request, filtro.errors)
        datos = {k: v for k, v in (filtro.cleaned_data or {}).items()}
    cliente_query = datos.get("cliente") or ""
    fecha_valor = datos.get("fecha")
    fecha_query = fecha_valor.isoformat() if fecha_valor else ""
    q = datos.get("q") or ""
    estado_query = datos.get("estado") or ""

    pedidos = buscar_pedidos_admin(cliente_query=cliente_query, fecha_query=fecha_valor, q=q)
    if estado:
        if isinstance(estado, (list, tuple, set)):
            pedidos = pedidos.filter(estado__in=estado)
        else:
            pedidos = pedidos.filter(estado=estado)
    if solo_autorizados_despacho:
        pedidos = pedidos.exclude(
            pago__estado__in=[Pago.PENDIENTE, Pago.RECHAZADO]
        ).exclude(estado__in=[Pedido.PENDIENTE, Pedido.CANCELADO])
    if estado_query:
        if estado_query == "pendiente_correccion_pago":
            pedidos = pedidos.filter(estado=Pedido.PENDIENTE, pago__estado=Pago.RECHAZADO)
        else:
            pedidos = pedidos.filter(estado=estado_query)

    has_filters = bool(cliente_query or fecha_query or q or estado_query)
    total_resultados = pedidos.count()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(
            request,
            "pedidos/_lista_body.html",
            {
                "pedidos": pedidos,
                "solo_autorizados_despacho": solo_autorizados_despacho,
                "es_historial": es_historial,
            },
        )

    context = {
        "pedidos": pedidos,
        "cliente_query": cliente_query,
        "fecha_query": fecha_query,
        "q": q,
        "estado_query": estado_query,
        "titulo_panel": titulo,
        "has_filters": has_filters,
        "total_resultados": total_resultados,
        "estado_actual": estado,
        "solo_autorizados_despacho": solo_autorizados_despacho,
        "es_historial": es_historial,
    }
    return render(request, "pedidos/lista.html", context)


@admin_required
def lista_pedidos_admin(request):
    return _render_lista_por_estado(
        request,
        [
            Pedido.PENDIENTE,
            Pedido.AUTORIZADO_DESPACHO,
            Pedido.VEHICULO_ASIGNADO,
        ],
        "Gestión de Pedidos",
    )


@admin_required
def lista_entregas_admin(request):
    return _render_lista_por_estado(
        request,
        [
            Pedido.AUTORIZADO_DESPACHO,
            Pedido.VEHICULO_ASIGNADO,
            Pedido.EN_RUTA,
            Pedido.ENTREGADO,
        ],
        "Control de Entregas y Envíos",
        solo_autorizados_despacho=True,
    )


@admin_required
def historial_pedidos_admin(request):
    return _render_lista_por_estado(
        request,
        [
            Pedido.ENTREGADO,
            Pedido.CANCELADO,
        ],
        "Historial de Pedidos (Entregados y Cancelados)",
        es_historial=True,
    )


def _obtener_recursos_transporte_para_pedido(orden):
    """
    Devuelve la tupla (conductores, vehiculos) disponibles para asignar a `orden`.
    Asegura que los usuarios con rol conductor activos tengan perfil Conductor
    y excluye recursos ocupados en otros envíos activos.
    """
    from apps.usuarios.models import Conductor

    for u in Usuario.objects.filter(
        rol="conductor",
        estado="activo",
        is_active=True,
        perfil_conductor__isnull=True,
    ):
        try:
            Conductor.ensure_for_user(u)
        except Exception:
            pass

    conductores_ocupados_ids = set(
        Entrega.objects.filter(
            Q(estado="en_ruta") | Q(pedido__estado=Pedido.EN_RUTA),
            conductor__isnull=False,
        )
        .exclude(pedido=orden)
        .values_list("conductor__usuario_id", flat=True)
    )
    # También cubrir pedidos en ruta que aún conservan la asignación en los
    # campos legacy del pedido, aunque no tengan una Entrega sincronizada.
    conductores_ocupados_ids.update(
        Pedido.objects.filter(estado=Pedido.EN_RUTA, conductor__isnull=False)
        .exclude(pk=orden.pk)
        .values_list("conductor__usuario_id", flat=True)
    )
    conductores_ocupados_ids.update(
        Pedido.objects.filter(estado=Pedido.EN_RUTA, conductor_usuario_legacy__isnull=False)
        .exclude(pk=orden.pk)
        .values_list("conductor_usuario_legacy_id", flat=True)
    )

    conductores = (
        Usuario.objects.filter(
            rol="conductor",
            estado="activo",
            is_active=True,
            perfil_conductor__estado="activo",
        )
        .exclude(pk__in=conductores_ocupados_ids)
        .select_related("perfil_conductor")
        .prefetch_related(
            Prefetch(
                "perfil_conductor__asignaciones_vehiculo",
                queryset=ConductorVehiculo.objects.filter(fecha_fin__isnull=True).select_related("vehiculo"),
                to_attr="asignaciones_activas",
            )
        )
        .order_by("nombres", "apellidos")
    )

    vehiculos_ocupados_ids = (
        Entrega.objects.filter(
            estado__in=["pendiente", "en_ruta"],
            pedido__estado__in=[
                Pedido.AUTORIZADO_DESPACHO,
                Pedido.VEHICULO_ASIGNADO,
                Pedido.EN_RUTA,
            ],
            vehiculo__isnull=False,
        )
        .exclude(pedido=orden)
        .values_list("vehiculo_id", flat=True)
    )

    vehiculos = (
        Vehiculo.objects.filter(
            Q(estado="disponible") | Q(entregas__pedido=orden, entregas__estado__in=["pendiente", "en_ruta"])
        )
        .exclude(pk__in=vehiculos_ocupados_ids)
        .distinct()
        .order_by("placa")
    )

    return conductores, vehiculos


@login_required
def ver_pedido_admin(request, id):
    orden = get_object_or_404(Pedido, codigo_pedido=id)
    verificar_y_cancelar_pedidos_por_vencimiento_correccion_pago(pedido=orden)
    orden.refresh_from_db()
    usuario_actual = request.user
    is_super = getattr(usuario_actual, "is_superuser", False) or getattr(
        usuario_actual, "es_superadmin", False
    )
    es_admin = is_super or usuario_actual.rol == "admin"

    cliente_dueno = orden.usuario_id == usuario_actual.pk or (
        orden.cliente is not None
        and orden.cliente.usuario_id is not None
        and orden.cliente.usuario_id == usuario_actual.pk
    )
    perfil_conductor = (
        usuario_actual.conductor_profile if usuario_actual.rol == "conductor" else None
    )
    conductor_asignado = bool(
        orden.conductor_usuario_legacy_id == usuario_actual.pk
        or (
            perfil_conductor is not None
            and (
                orden.conductor_id == perfil_conductor.pk
                or orden.entregas.filter(conductor_id=perfil_conductor.pk).exists()
            )
        )
    )

    if not es_admin:
        if usuario_actual.rol == "cliente" and not cliente_dueno:
            ip = obtener_ip(request)
            registrar_warning(ip)
            registrar_evento(
                request,
                "role_violation",
                gravedad="high",
                detalles={
                    "causa": "ver_pedido_ajeno",
                    "codigo_pedido": orden.codigo_pedido,
                    "rol_usuario": "cliente",
                    "cliente_pedido_id": orden.cliente_id,
                },
            )
            return _respuesta_no_autorizada(
                request,
                detalles={
                    "rol_requerido": ["admin"],
                    "permiso_alternativo": "propietario del pedido",
                    "codigo_pedido": orden.codigo_pedido,
                },
            )
        if usuario_actual.rol == "conductor" and not conductor_asignado:
            ip = obtener_ip(request)
            registrar_warning(ip)
            registrar_evento(
                request,
                "role_violation",
                gravedad="high",
                detalles={
                    "causa": "conductor_ver_pedido_no_asignado",
                    "codigo_pedido": orden.codigo_pedido,
                    "rol_usuario": "conductor",
                },
            )
            return _respuesta_no_autorizada(
                request,
                detalles={
                    "rol_requerido": ["admin"],
                    "permiso_alternativo": "conductor asignado al pedido",
                    "codigo_pedido": orden.codigo_pedido,
                },
            )
        if usuario_actual.rol not in ("admin", "cliente", "conductor"):
            ip = obtener_ip(request)
            registrar_warning(ip)
            registrar_evento(
                request,
                "role_violation",
                gravedad="high",
                detalles={
                    "causa": "rol_no_autorizado_ver_pedido",
                    "codigo_pedido": orden.codigo_pedido,
                    "rol_usuario": usuario_actual.rol,
                },
            )
            return _respuesta_no_autorizada(
                request,
                detalles={
                    "rol_requerido": ["admin", "cliente", "conductor"],
                    "rol_usuario": usuario_actual.rol,
                },
            )

    if request.method == "POST":
        accion = request.POST.get("accion")
        nuevo_estado = request.POST.get("estado")

        if usuario_actual.rol == "conductor" and not es_admin:
            if accion in ("iniciar_ruta", "confirmar", "cancelar") and not conductor_asignado:
                ip = obtener_ip(request)
                registrar_warning(ip)
                registrar_evento(
                    request,
                    "role_violation",
                    gravedad="high",
                    detalles={
                        "causa": "conductor_modificar_pedido_no_asignado",
                        "codigo_pedido": orden.codigo_pedido,
                        "accion": accion,
                    },
                )
                return _respuesta_no_autorizada(
                    request,
                    detalles={
                        "rol_requerido": ["admin"],
                        "permiso_alternativo": "conductor asignado",
                        "codigo_pedido": orden.codigo_pedido,
                    },
                )
            if accion == "iniciar_ruta":
                try:
                    confirmar_preparacion_e_iniciar_ruta(orden, request.user)
                    registrar_actividad(
                        request,
                        "iniciar_entrega",
                        "pedidos",
                        orden.codigo_pedido,
                        f"Conductor {request.user.username} confirmó preparación e inició ruta del pedido #{orden.codigo_pedido}",
                    )
                    messages.success(
                        request,
                        f"Preparación confirmada. El pedido #{orden.codigo_pedido} está ahora «En Ruta».",
                    )
                except ValidationError as exc:
                    _mensajes_error(request, exc)
                return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

            if accion == "confirmar":
                observacion = request.POST.get("observacion", "").strip()[:2000]
                try:
                    marcar_pedido_entregado(orden, request.user, observacion=observacion)
                    registrar_actividad(
                        request,
                        "confirmar_entrega",
                        "pedidos",
                        orden.codigo_pedido,
                        "Conductor confirmó entrega exitosa"
                        + (f". Observación: {observacion}" if observacion else ""),
                    )
                    messages.success(
                        request,
                        f"¡Entrega del pedido #{orden.codigo_pedido} confirmada con éxito!",
                    )
                except ValidationError as exc:
                    _mensajes_error(request, exc)
                return redirect("usuarios:panel")

            elif accion == "cancelar":
                motivo = request.POST.get("motivo", "").strip()
                try:
                    cancelar_envio_pedido(orden, request.user, motivo=motivo)
                    registrar_actividad(
                        request,
                        "cancelar_entrega",
                        "pedidos",
                        orden.codigo_pedido,
                        f"Conductor canceló la entrega: {motivo}",
                    )
                    messages.warning(
                        request, f"Entrega del pedido #{orden.codigo_pedido} cancelada."
                    )
                except ValidationError as exc:
                    _mensajes_error(request, exc)
                    return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)
                return redirect("usuarios:panel")

        elif usuario_actual.rol == "cliente" and cliente_dueno and not es_admin:
            if accion == "cancelar":
                motivo = request.POST.get("motivo", "").strip()
                if orden.estado != Pedido.PENDIENTE:
                    messages.error(request, "Solo se pueden cancelar pedidos en estado pendiente.")
                    return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)
                db_alias = "remota" if debe_usar_bd_remota() else "default"
                try:
                    cancelar_envio_pedido(orden, request.user, motivo=motivo, using=db_alias)
                    registrar_actividad(
                        request,
                        "cancelar_pedido",
                        "pedidos",
                        orden.codigo_pedido,
                        f"Cliente canceló el pedido #{orden.codigo_pedido}. Motivo: {motivo}",
                    )
                    messages.warning(
                        request,
                        f"El pedido #{orden.codigo_pedido} ha sido cancelado y el stock devuelto.",
                    )
                except ValidationError as exc:
                    _mensajes_error(request, exc)
                return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

        elif es_admin:
            if accion == "asignar_transporte":
                if not orden.puede_despacharse:
                    messages.error(
                        request,
                        "No se puede asignar conductor ni vehículo porque el pago del pedido aún no ha sido aprobado.",
                    )
                    return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

                conductor_id = request.POST.get("conductor")
                vehiculo_id = request.POST.get("vehiculo")
                if not conductor_id:
                    messages.error(request, "Por favor selecciona un conductor disponible.")
                    return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)
                if not vehiculo_id:
                    usuario_cond_tmp = Usuario.objects.filter(pk=conductor_id, rol="conductor").first()
                    perfil_tmp = getattr(usuario_cond_tmp, "perfil_conductor", None) if usuario_cond_tmp else None
                    veh_actual = getattr(perfil_tmp, "vehiculo_actual", None) if perfil_tmp else None
                    if veh_actual:
                        vehiculo_id = veh_actual.pk
                if not vehiculo_id:
                    messages.error(request, "Por favor selecciona un vehículo disponible.")
                    return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

                try:
                    entrega_asig = asignar_conductor_y_vehiculo(
                        orden,
                        conductor_id,
                        vehiculo_id,
                        usuario_admin=request.user,
                    )
                    usuario_conductor = entrega_asig.conductor.usuario
                    vehiculo_bloqueado = entrega_asig.vehiculo
                    registrar_actividad(
                        request,
                        "editar",
                        "entrega",
                        entrega_asig.id_entrega,
                        f"Envío de pedido #{orden.codigo_pedido} asignado a {usuario_conductor.nombre_mostrar} con vehículo {vehiculo_bloqueado.placa}",
                    )
                    messages.success(
                        request,
                        f"Conductor {usuario_conductor.nombre_mostrar} y vehículo {vehiculo_bloqueado.placa} asignados correctamente al pedido #{orden.codigo_pedido}. "
                        f"El pedido autorizado para despacho ya fue enviado al panel del conductor.",
                    )
                except ValidationError as exc:
                    _mensajes_error(request, exc)
                return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

            if accion == "iniciar_ruta":
                try:
                    confirmar_preparacion_e_iniciar_ruta(orden, request.user)
                    registrar_actividad(
                        request,
                        "iniciar_entrega",
                        "pedidos",
                        orden.codigo_pedido,
                        f"Administrador {request.user.username} confirmó preparación e inició ruta del pedido #{orden.codigo_pedido}",
                    )
                    messages.success(
                        request,
                        f"Preparación confirmada e inicio de ruta registrado para el pedido #{orden.codigo_pedido}.",
                    )
                except ValidationError as exc:
                    _mensajes_error(request, exc)
                return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

            if accion == "confirmar":
                observacion = request.POST.get("observacion", "").strip()[:2000]
                try:
                    marcar_pedido_entregado(orden, request.user, observacion=observacion)
                    registrar_actividad(
                        request,
                        "confirmar_entrega",
                        "pedidos",
                        orden.codigo_pedido,
                        f"Administrador {request.user.username} marcó como entregado el pedido #{orden.codigo_pedido}",
                    )
                    messages.success(
                        request,
                        f"El pedido #{orden.codigo_pedido} fue marcado como «Entregado».",
                    )
                except ValidationError as exc:
                    _mensajes_error(request, exc)
                return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

            if accion == "cancelar":
                motivo = request.POST.get("motivo", "").strip()
                try:
                    cancelar_envio_pedido(orden, request.user, motivo=motivo)
                    registrar_actividad(
                        request,
                        "cancelar_entrega",
                        "pedidos",
                        orden.codigo_pedido,
                        f"Administrador canceló el envío del pedido #{orden.codigo_pedido}. Motivo: {motivo}",
                    )
                    messages.warning(
                        request,
                        f"El envío del pedido #{orden.codigo_pedido} fue cancelado.",
                    )
                except ValidationError as exc:
                    _mensajes_error(request, exc)
                return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

            form = CambioEstadoPedidoForm(request.POST)
            if not form.is_valid():
                _mensajes_error(request, form.errors)
                return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)
            nuevo_estado = form.cleaned_data["estado"]
            db_alias = "remota" if debe_usar_bd_remota() else "default"
            try:
                if nuevo_estado == orden.estado:
                    messages.info(request, "El pedido ya se encuentra en ese estado.")
                    return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

                if (
                    nuevo_estado in Pedido.ESTADOS_REQUIEREN_PAGO
                    and not orden.puede_despacharse
                ):
                    raise ValidationError(
                        {"estado": "No se autoriza el despacho sin un pago aprobado."}
                    )

                if nuevo_estado == Pedido.AUTORIZADO_DESPACHO:
                    autorizar_despacho_por_pago(orden, usuario_admin=request.user)
                elif nuevo_estado == Pedido.EN_RUTA:
                    confirmar_preparacion_e_iniciar_ruta(orden, request.user)
                elif nuevo_estado == Pedido.ENTREGADO:
                    marcar_pedido_entregado(
                        orden,
                        request.user,
                        observacion=request.POST.get("observacion", ""),
                    )
                elif nuevo_estado == Pedido.CANCELADO:
                    motivo_form = (
                        request.POST.get("motivo", "").strip()
                        or "Cancelación administrativa desde control de estado"
                    )
                    cancelar_envio_pedido(orden, request.user, motivo=motivo_form, using=db_alias)
                else:
                    with transaction.atomic():
                        orden = Pedido.objects.select_for_update().get(pk=orden.pk)
                        orden.transicionar(nuevo_estado)
                        orden.full_clean(exclude=["fecha_entrega_programada"])
                        orden.save()

                registrar_actividad(
                    request,
                    "editar",
                    "pedidos",
                    orden.codigo_pedido,
                    f"Estado de pedido cambiado por admin a: {nuevo_estado}",
                )
            except ValidationError as exc:
                _mensajes_error(request, exc)
                return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)
            messages.success(
                request,
                f"Estado del pedido #{orden.codigo_pedido} actualizado a {orden.get_estado_display()}.",
            )
            return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

    entrega = (
        orden.entregas.select_related(
            "conductor__usuario",
            "vehiculo",
            "confirmado_salida_por",
            "entregado_por",
        ).first()
    )
    conductor_usuario = (
        (entrega.conductor.usuario if entrega and entrega.conductor else None)
        or orden.conductor_usuario
    )
    vehiculo = entrega.vehiculo if entrega else None
    pago = orden.pago_actual

    conductores_disponibles = []
    vehiculos_disponibles = []
    puede_asignar_transporte = bool(
        es_admin
        and orden.puede_despacharse
        and orden.estado not in (Pedido.EN_RUTA, Pedido.ENTREGADO, Pedido.CANCELADO)
    )
    if es_admin and orden.estado not in (Pedido.EN_RUTA, Pedido.ENTREGADO, Pedido.CANCELADO):
        conductores_disponibles, vehiculos_disponibles = _obtener_recursos_transporte_para_pedido(orden)

    context = {
        "orden": orden,
        "entrega": entrega,
        "conductor_usuario": conductor_usuario,
        "vehiculo": vehiculo,
        "pago": pago,
        "conductores_disponibles": conductores_disponibles,
        "vehiculos_disponibles": vehiculos_disponibles,
        "puede_asignar_transporte": puede_asignar_transporte,
        "puede_iniciar_ruta": (
            (es_admin or (usuario_actual.rol == "conductor" and conductor_asignado))
            and orden.estado in (Pedido.VEHICULO_ASIGNADO, Pedido.AUTORIZADO_DESPACHO)
            and orden.puede_despacharse
            and entrega is not None
            and bool(entrega.conductor_id and entrega.vehiculo_id)
        ),
        "puede_confirmar_entrega": (
            (es_admin or (usuario_actual.rol == "conductor" and conductor_asignado))
            and orden.estado == Pedido.EN_RUTA
        ),
    }
    return render(request, "pedidos/detalle.html", context)


@admin_required
def crear_entrega(request, orden_id):
    orden = get_object_or_404(
        Pedido.objects.select_related("usuario", "cliente__usuario").prefetch_related("detalles__material"),
        codigo_pedido=orden_id,
    )

    if not orden.puede_despacharse:
        messages.error(
            request,
            "Este pedido no cuenta con un pago aprobado ni cumple las condiciones comerciales para despacho.",
        )
        return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

    conductores, vehiculos = _obtener_recursos_transporte_para_pedido(orden)

    total_peso_estimado = sum((d.cantidad for d in orden.detalles.all()), 0)

    if request.method == "POST":
        conductor_id = request.POST.get("conductor")
        vehiculo_id = request.POST.get("vehiculo")

        if not conductor_id:
            messages.error(request, "Por favor selecciona un conductor activo.")
            return render(
                request,
                "pedidos/asignar_entrega.html",
                {
                    "orden": orden,
                    "conductores": conductores,
                    "vehiculos": vehiculos,
                    "total_peso": total_peso_estimado,
                },
                status=400,
            )

        if not vehiculo_id:
            usuario_cond_tmp = Usuario.objects.filter(pk=conductor_id, rol="conductor").first()
            perfil_tmp = getattr(usuario_cond_tmp, "perfil_conductor", None) if usuario_cond_tmp else None
            veh_actual = perfil_tmp.vehiculo_actual if perfil_tmp else None
            if veh_actual:
                vehiculo_id = veh_actual.pk

        try:
            entrega = asignar_conductor_y_vehiculo(
                orden,
                conductor_id,
                vehiculo_id,
                usuario_admin=request.user,
            )
        except ValidationError as exc:
            _mensajes_error(request, exc)
            return render(
                request,
                "pedidos/asignar_entrega.html",
                {
                    "orden": orden,
                    "conductores": conductores,
                    "vehiculos": vehiculos,
                    "total_peso": total_peso_estimado,
                },
                status=400,
            )

        usuario_conductor = entrega.conductor.usuario
        vehiculo_bloqueado = entrega.vehiculo
        registrar_actividad(
            request,
            "editar",
            "entrega",
            entrega.id_entrega,
            f"Envío de pedido #{orden.codigo_pedido} asignado a {usuario_conductor.nombre_mostrar} con vehículo {vehiculo_bloqueado.placa}",
        )

        messages.success(
            request,
            f"Envío del pedido #{orden.codigo_pedido} asignado correctamente a {usuario_conductor.nombre_mostrar} "
            f"con vehículo {vehiculo_bloqueado.placa}. Queda en estado «Vehículo Asignado» listo para preparación e inicio de ruta.",
        )
        return redirect("pedidos:lista_entregas_admin")

    context = {
        "orden": orden,
        "conductores": conductores,
        "vehiculos": vehiculos,
        "total_peso": total_peso_estimado,
    }
    return render(request, "pedidos/asignar_entrega.html", context)



@admin_required
@require_POST
def eliminar_orden(request, id):
    orden = get_object_or_404(Pedido, codigo_pedido=id)
    order_id = orden.codigo_pedido
    db_alias = "remota" if debe_usar_bd_remota() else "default"

    try:
        with transaction.atomic(using=db_alias):
            if orden.estado not in (Pedido.ENTREGADO, Pedido.CANCELADO):
                revertir_stock_pedido(orden, request.user, "Eliminación", using=db_alias)
            liberar_vehiculo_pedido(orden)
    except DatabaseError as exc:
        logger.error("Error BD al limpiar pedido %s: %s", order_id, exc)
        messages.error(request, "No fue posible eliminar el pedido por un error de base de datos.")
        return redirect("pedidos:lista_pedidos_admin")
    except Exception as exc:
        logger.error("Error limpiando pedido %s: %s", order_id, exc, exc_info=True)
        messages.error(request, "No fue posible preparar el pedido para su eliminación.")
        return redirect("pedidos:lista_pedidos_admin")

    registrar_actividad(
        request,
        "eliminar",
        "pedidos",
        order_id,
        f"Pedido #{order_id} eliminado definitivamente por admin",
    )
    orden.delete()
    messages.success(request, f"Pedido #{order_id} eliminado correctamente.")
    return redirect("pedidos:lista_pedidos_admin")


# ========== Solicitudes (gestion_pedidos) ==========

def _crear_solicitud_pedido(usuario, items, descuento):
    with transaction.atomic():
        pedido = SolicitudPedido.objects.create(
            cliente=usuario, descuento=descuento, estado="pendiente"
        )

        bruto = Decimal("0")
        for material_id, cantidad in items:
            material = MaterialConstruccion.objects.filter(pk=material_id).first()
            if material is None:
                raise ValueError("Uno de los materiales seleccionados no existe.")
            stock_obj = select_for_update_if_supported(Stock.objects, "default").filter(
                material=material
            ).first()
            if stock_obj is None:
                raise ValueError("Uno de los materiales no tiene inventario.")

            if stock_obj.cantidad_actual < cantidad:
                raise ValueError(
                    f"Stock insuficiente para {material.nombre}. Disponible: {stock_obj.cantidad_actual}"
                )

            stock_obj.cantidad_actual -= cantidad
            stock_obj.save()

            DetalleSolicitudPedido.objects.create(
                pedido=pedido, material=material, cantidad=cantidad
            )
            bruto += material.precio * cantidad

        if descuento > bruto:
            raise ValueError("El descuento no puede superar el subtotal del pedido.")

    return pedido


@role_required(["admin", "cliente"])

@login_required
@transaction.atomic
def crear_pedido(request):
    materiales = MaterialConstruccion.objects.all()

    if request.method == "POST":
        materiales_ids = request.POST.getlist("materiales[]")
        cantidades = request.POST.getlist("cantidades[]")

        if (
            not materiales_ids
            or len(materiales_ids) > 50
            or len(materiales_ids) != len(cantidades)
        ):
            messages.error(request, "El pedido debe incluir entre 1 y 50 líneas válidas.")
            context = {"materiales": materiales}
            return render(request, "pedidos/crear_pedido.html", context)

        items = []
        vistos = set()
        try:
            for material_id, cantidad_raw in zip(materiales_ids, cantidades, strict=True):
                if (
                    not material_id.isdecimal()
                    or not cantidad_raw.isdecimal()
                ):
                    raise ValueError("El formulario contiene materiales o cantidades inválidos.")
                material_pk = int(material_id)
                if material_pk in vistos:
                    raise ValueError("El formulario contiene materiales o cantidades inválidos.")
                cantidad = int(cantidad_raw)
                if not 1 <= cantidad <= 100000:
                    raise ValueError("Cada cantidad debe estar entre 1 y 100000.")
                vistos.add(material_pk)
                items.append((material_pk, cantidad))

            descuento = Decimal(request.POST.get("descuento", "0"))
            if not descuento.is_finite() or descuento < 0:
                raise ValueError("El descuento debe ser un monto válido no negativo.")
            if (
                descuento > Decimal("99999999.99")
                or descuento != descuento.quantize(Decimal("0.01"))
            ):
                raise ValueError("El descuento debe tener como máximo dos decimales.")
            if descuento and request.user.rol != "admin":
                raise ValueError("Solo un administrador puede aplicar un descuento.")

            pedido = _crear_solicitud_pedido(request.user, items, descuento)
            pedido = SolicitudPedido.objects.create(
                cliente=request.user, descuento=descuento, estado="pendiente"
            )

            for m_id, cant in zip(materiales_ids, cantidades, strict=False):
                cant = int(cant)
                material = get_object_or_404(MaterialConstruccion, pk=m_id)
                stock_obj = select_for_update_if_supported(Stock.objects, "default").get(
                    material=material
                )

                if stock_obj.cantidad_actual < cant:
                    raise ValueError(
                        f"Stock insuficiente para {material.nombre}. Disponible: {stock_obj.cantidad_actual}"
                    )

                stock_obj.cantidad_actual -= cant
                stock_obj.save()

                DetalleSolicitudPedido.objects.create(
                    pedido=pedido, material=material, cantidad=cant
                )

            messages.success(request, f"Solicitud #{pedido.id} creada exitosamente.")
            return redirect("pedidos:lista_solicitudes")

        except (InvalidOperation, ValueError) as exc:
            messages.error(request, str(exc))

    context = {"materiales": materiales}
    return render(request, "pedidos/crear_pedido.html", context)


@login_required
def listar_pedidos(request):
    if request.user.rol == "admin":
        pedidos = SolicitudPedido.objects.all()
    else:
        pedidos = SolicitudPedido.objects.filter(cliente=request.user)

    context = {"pedidos": pedidos}
    return render(request, "pedidos/listar_pedidos.html", context)


@login_required
def detalle_pedido(request, pk):
    pedido = get_object_or_404(SolicitudPedido, pk=pk)

    if request.user.rol != "admin" and pedido.cliente != request.user:
        messages.error(request, "No tiene permisos para ver esta solicitud.")
        return redirect("pedidos:lista_solicitudes")

    context = {"pedido": pedido}
    return render(request, "pedidos/detalle_pedido.html", context)


@admin_required
@require_POST
@transaction.atomic
def aprobar_pedido(request, pk):
    pedido = get_object_or_404(SolicitudPedido.objects.select_for_update(), pk=pk)
    if pedido.puede_transicionar("aprobado") and pedido.estado != "aprobado":
        pedido.transicionar("aprobado")
        pedido.save()
        messages.success(request, f"Solicitud #{pedido.id} aprobada.")
    else:
        messages.warning(request, "Solo se pueden aprobar solicitudes en estado pendiente.")

    return redirect("pedidos:detalle_solicitud", pk=pk)


@admin_required
@require_POST
@transaction.atomic
def cancelar_pedido(request, pk):
    pedido = get_object_or_404(SolicitudPedido.objects.select_for_update(), pk=pk)
    if pedido.puede_transicionar("cancelado") and pedido.estado != "cancelado":
        for detalle in pedido.detalles.all():
            stock_obj = select_for_update_if_supported(Stock.objects, "default").get(
                material=detalle.material
            )
            stock_obj.cantidad_actual += detalle.cantidad
            stock_obj.save()

        pedido.transicionar("cancelado")
        pedido.save()
        messages.success(request, f"Solicitud #{pedido.id} cancelada y stock devuelto.")
    else:
        messages.warning(request, "Esta solicitud no puede ser cancelada.")

    return redirect("pedidos:detalle_solicitud", pk=pk)


@login_required
def estado_pedido_api(request, id):
    orden = get_object_or_404(Pedido, codigo_pedido=id)
    verificar_y_cancelar_pedidos_por_vencimiento_correccion_pago(pedido=orden)
    orden.refresh_from_db()
    usuario_actual = request.user
    is_super = getattr(usuario_actual, "is_superuser", False) or getattr(
        usuario_actual, "es_superadmin", False
    )
    es_admin = is_super or getattr(usuario_actual, "rol", "") == "admin"
    cliente_dueno = (orden.usuario_id == usuario_actual.pk) or (
        orden.cliente is not None and orden.cliente.usuario_id == usuario_actual.pk
    )
    perfil_conductor = (
        getattr(usuario_actual, "conductor_profile", None)
        if getattr(usuario_actual, "rol", "") == "conductor"
        else None
    )
    conductor_asignado = bool(
        orden.conductor_usuario_legacy_id == usuario_actual.pk
        or (
            perfil_conductor is not None
            and (
                orden.conductor_id == perfil_conductor.pk
                or orden.entregas.filter(conductor_id=perfil_conductor.pk).exists()
            )
        )
    )

    if not (es_admin or cliente_dueno or conductor_asignado):
        return JsonResponse({"error": "No autorizado"}, status=403)

    entrega = orden.entregas.select_related("conductor__usuario", "vehiculo").first()
    conductor_usuario = (
        (entrega.conductor.usuario if entrega and entrega.conductor else None)
        or orden.conductor_usuario
    )
    vehiculo = entrega.vehiculo if entrega else None
    pago = orden.pago_actual

    data = {
        "codigo_pedido": orden.codigo_pedido,
        "estado": orden.estado,
        "estado_display": orden.estado_gestion_display,
        "estado_logistico_display": orden.estado_logistico_display,
        "requiere_correccion_pago": orden.requiere_correccion_pago,
        "fecha_solicitud": (
            orden.fecha_solicitud.strftime("%d/%m/%Y %H:%M") if orden.fecha_solicitud else ""
        ),
        "pago": {
            "existe": bool(pago),
            "estado": pago.estado if pago else None,
            "estado_display": pago.estado_gestion_display if pago else "Sin registrar",
            "requiere_correccion": pago.requiere_correccion if pago else False,
            "metodo": pago.metodo if pago else "",
            "metodo_display": pago.get_metodo_display() if pago else "",
            "fecha_revision": (
                pago.fecha_revision.strftime("%d/%m/%Y %H:%M")
                if (pago and pago.fecha_revision)
                else ""
            ),
        },
        "logistica": {
            "fecha_toma_entrega": (
                orden.fecha_toma_entrega.strftime("%d/%m/%Y %H:%M")
                if orden.fecha_toma_entrega
                else ""
            ),
            "fecha_entrega_real": (
                orden.fecha_entrega_real.strftime("%d/%m/%Y %H:%M")
                if orden.fecha_entrega_real
                else ""
            ),
            "conductor": (
                f"{conductor_usuario.nombres} {conductor_usuario.apellidos}"
                if conductor_usuario
                else None
            ),
            "conductor_telefono": (
                getattr(conductor_usuario, "telefono", "") if conductor_usuario else ""
            ),
            "vehiculo_placa": vehiculo.placa if vehiculo else None,
            "vehiculo_desc": (
                f"{vehiculo.marca} {vehiculo.modelo}" if vehiculo else None
            ),
        },
    }
    return JsonResponse(data)


from apps.pedidos.views_pagos import *  # noqa: F401,F403

