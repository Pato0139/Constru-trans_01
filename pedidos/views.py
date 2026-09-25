from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, DatabaseError
from django.db.models import F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
import logging

from core.security import (
    _respuesta_no_autorizada,
    obtener_ip,
    registrar_evento,
    registrar_warning,
)
from auditoria.utils import registrar_actividad
from catalogo.models.movimientos import MovimientoInventario
from catalogo.models import MaterialConstruccion, Stock
from usuarios.models import Conductor, Usuario
from usuarios.views import admin_required
from core.db_preference import debe_usar_bd_remota
from core.db_utils import select_for_update_if_supported

from .models import (
    DetalleOrden,
    DetallePedido,
    DetalleSolicitudPedido,
    Orden,
    Pedido,
    SolicitudPedido,
)
from .utils import liberar_vehiculo_pedido, revertir_stock_pedido

logger = logging.getLogger(__name__)


@admin_required
def calcular_total(request, id):
    orden = get_object_or_404(Orden, codigo_pedido=id)
    total = orden.calcular_total()
    return JsonResponse({"total": float(total)})


@admin_required
def eliminar_detalle(request, id):
    detalle = get_object_or_404(DetalleOrden, id_detalle_pedido=id)
    orden = detalle.pedido
    db_alias = "remota" if debe_usar_bd_remota() else "default"

    with transaction.atomic():
        with transaction.atomic(using=db_alias):
            stock_obj = (
                select_for_update_if_supported(Stock.objects.using(db_alias), db_alias).get(
                    material=detalle.material
                )
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
    orden = get_object_or_404(Orden, codigo_pedido=id)
    materiales = MaterialConstruccion.objects.all()
    detalles = orden.detalles.all()

    if request.method == "POST":
        material_id = request.POST.get("material")
        try:
            cantidad = int(request.POST.get("cantidad", 0) or 0)
        except (TypeError, ValueError):
            messages.error(request, "La cantidad debe ser un entero.")
            return redirect("pedidos:agregar_materiales", id=orden.codigo_pedido)

        if cantidad < 1:
            messages.error(request, "La cantidad mínima es 1.")
            return redirect("pedidos:agregar_materiales", id=orden.codigo_pedido)

        if material_id:
            material = get_object_or_404(MaterialConstruccion, pk=material_id)
            stock_obj = Stock.objects.get(material=material)

            if stock_obj.cantidad_actual >= cantidad:
                with transaction.atomic():
                    detalle, created = DetalleOrden.objects.get_or_create(
                        pedido=orden,
                        material=material,
                        defaults={
                            "cantidad": cantidad,
                            "precio_unitario": material.precio_referencia,
                        },
                    )
                    if not created:
                        detalle.cantidad += cantidad
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
            else:
                messages.error(request, "Stock insuficiente")

        return redirect("pedidos:agregar_materiales", id=orden.codigo_pedido)

    context = {"orden": orden, "materiales": materiales, "detalles": detalles}
    return render(request, "pedidos/agregar_materiales.html", context)


def buscar_pedidos_admin(cliente_query=None, fecha_query=None, q=None, estado=None):
    pedidos = (
        Orden.objects.all()
        .select_related("usuario", "cliente", "conductor")
        .prefetch_related("detalles__material", "entregas")
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
def _render_lista_por_estado(request, estado, titulo):
    cliente_query = request.GET.get("cliente", "").strip()
    fecha_query = request.GET.get("fecha", "").strip()
    q = request.GET.get("q", "").strip()

    pedidos = buscar_pedidos_admin(cliente_query=cliente_query, fecha_query=fecha_query, q=q)
    if estado:
        pedidos = pedidos.filter(estado=estado)

    has_filters = bool(cliente_query or fecha_query or q)
    total_resultados = pedidos.count()

    context = {
        "pedidos": pedidos,
        "cliente_query": cliente_query,
        "fecha_query": fecha_query,
        "q": q,
        "titulo_panel": titulo,
        "has_filters": has_filters,
        "total_resultados": total_resultados,
        "estado_actual": estado,
    }
    return render(request, "pedidos/lista.html", context)


@admin_required
def lista_pedidos_admin(request):
    return _render_lista_por_estado(request, Orden.PENDIENTE, "Ventas Pendientes")


@admin_required
def lista_entregas_admin(request):
    return _render_lista_por_estado(request, Orden.EN_RUTA, "Control de Entregas")


@login_required
def ver_pedido_admin(request, id):
    orden = get_object_or_404(Orden, codigo_pedido=id)
    usuario_actual = request.user
    is_super = getattr(usuario_actual, "is_superuser", False) or getattr(usuario_actual, "es_superadmin", False)
    es_admin = is_super or usuario_actual.rol == "admin"

    cliente_dueno = (
        orden.cliente is not None
        and orden.cliente.usuario_id is not None
        and orden.cliente.usuario_id == usuario_actual.pk
    )
    conductor_asignado = bool(
        orden.entregas.filter(conductor_id=getattr(usuario_actual, "pk", None)).exists()
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
            if accion in ("confirmar", "cancelar") and not conductor_asignado:
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
            if accion == "confirmar":
                if orden.estado != Orden.ENTREGADO:
                    with transaction.atomic():
                        entrega = orden.entregas.filter(conductor=usuario_actual).first()
                        if entrega:
                            entrega.estado = "entregado"
                            entrega.save()

                            if entrega.vehiculo:
                                entrega.vehiculo.estado = "disponible"
                                entrega.vehiculo.save()

                            registrar_actividad(
                                request,
                                "confirmar_entrega",
                                "pedidos",
                                orden.codigo_pedido,
                                "Conductor confirmó entrega exitosa",
                            )
                            messages.success(
                                request,
                                f"¡Entrega del pedido #{orden.codigo_pedido} confirmada con éxito!",
                            )
                        else:
                            messages.error(
                                request, "No tienes una entrega asignada para este pedido."
                            )
                return redirect("usuarios:panel")

            elif accion == "cancelar":
                if orden.estado not in (Orden.ENTREGADO, Orden.CANCELADO):
                    db_alias = "remota" if debe_usar_bd_remota() else "default"
                    with transaction.atomic():
                        with transaction.atomic(using=db_alias):
                            liberar_vehiculo_pedido(orden)
                            revertir_stock_pedido(
                                orden, request.user, "Cancelación (Conductor)", using=db_alias
                            )

                        orden.estado = Orden.CANCELADO
                        orden.save()

                        registrar_actividad(
                            request,
                            "cancelar_entrega",
                            "pedidos",
                            orden.codigo_pedido,
                            "Conductor canceló la entrega",
                        )
                        messages.warning(
                            request, f"Entrega del pedido #{orden.codigo_pedido} cancelada."
                        )
                return redirect("usuarios:panel")

        elif es_admin:
            if orden.estado == Orden.CANCELADO and nuevo_estado and nuevo_estado != Orden.CANCELADO:
                messages.info(request, "El pedido está cancelado. Solo se permite su consulta.")
                return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)
            db_alias = "remota" if debe_usar_bd_remota() else "default"
            if nuevo_estado:
                with transaction.atomic():
                    if nuevo_estado == Orden.ENTREGADO and orden.estado != Orden.ENTREGADO:
                        entrega = orden.entregas.first()
                        if entrega:
                            entrega.estado = "entregado"
                            if not entrega.fecha_entrega:
                                entrega.fecha_entrega = timezone.now()
                            entrega.save()
                            orden.estado = Orden.ENTREGADO
                            orden.fecha_entrega_real = timezone.now()
                            orden.save()
                        else:
                            messages.error(
                                request, "Para marcar como entregado primero asigna una entrega."
                            )
                            return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)
                    else:
                        if nuevo_estado == Orden.CANCELADO and orden.estado != Orden.CANCELADO:
                            with transaction.atomic(using=db_alias):
                                liberar_vehiculo_pedido(orden)
                                revertir_stock_pedido(
                                    orden, request.user, "Cancelación (Admin)", using=db_alias
                                )

                        orden.estado = nuevo_estado
                        if nuevo_estado == Orden.EN_RUTA and not orden.fecha_toma_entrega:
                            orden.fecha_toma_entrega = timezone.now()
                        orden.save()

                    registrar_actividad(
                        request,
                        "editar",
                        "pedidos",
                        orden.codigo_pedido,
                        f"Estado de pedido cambiado por admin a: {nuevo_estado}",
                    )
                    messages.success(
                        request,
                        f"Estado del pedido #{orden.codigo_pedido} actualizado a {nuevo_estado}.",
                    )
                return redirect("pedidos:ver_pedido_admin", id=orden.codigo_pedido)

    context = {"orden": orden}
    return render(request, "pedidos/detalle.html", context)


@admin_required
def crear_entrega(request, orden_id):
    orden = get_object_or_404(Orden, codigo_pedido=orden_id)
    conductores = (
        Usuario.objects.filter(
            rol="conductor", perfil_conductor__asignaciones_vehiculo__fecha_fin__isnull=True
        )
        .distinct()
        .select_related("perfil_conductor")
        .order_by("nombres", "apellidos")
    )

    if request.method == "POST":
        conductor_id = request.POST.get("conductor")

        if conductor_id:
            with transaction.atomic():
                conductor = get_object_or_404(Usuario, id=conductor_id)
                vehiculo = conductor.vehiculo_actual

                if not vehiculo:
                    messages.error(
                        request,
                        f"El conductor {conductor.nombres} no tiene un vehículo asignado. "
                        "Por favor, asígnale uno en la gestión de usuarios.",
                    )
                    context = {"orden": orden, "conductores": conductores}
                    return render(request, "pedidos/asignar_entrega.html", context)

                if orden.conductor and orden.conductor != conductor:
                    vehiculo_anterior = orden.conductor.vehiculo_actual
                    if vehiculo_anterior:
                        vehiculo_anterior.estado = "disponible"
                        vehiculo_anterior.save()

                from logistica.models import Entrega

                entrega, created = Entrega.objects.get_or_create(
                    pedido=orden,
                    defaults={
                        "conductor": conductor,
                        "vehiculo": vehiculo,
                        "estado": "en_ruta",
                        "direccion_entrega": orden.direccion_destino,
                    },
                )

                if not created:
                    if entrega.estado == "entregado":
                        messages.warning(
                            request,
                            f"La entrega del pedido #{orden.codigo_pedido} ya fue marcada como entregada. "
                            "No se puede reasignar automáticamente.",
                        )
                        return redirect("pedidos:lista_pedidos_admin")

                    entrega.conductor = conductor
                    entrega.vehiculo = vehiculo
                    entrega.estado = "en_ruta"
                    entrega.direccion_entrega = orden.direccion_destino
                    entrega.save()

                orden.estado = Orden.EN_RUTA
                orden.conductor = conductor
                if not orden.fecha_toma_entrega:
                    orden.fecha_toma_entrega = timezone.now()
                orden.save()

                vehiculo.estado = "en_ruta"
                vehiculo.save()

                accion = "reasignado" if not created else "asignado"
                registrar_actividad(
                    request,
                    "editar",
                    "pedidos",
                    orden.codigo_pedido,
                    f"Pedido {accion} a conductor: {conductor.nombres} con vehículo {vehiculo.placa}",
                )
                messages.success(
                    request,
                    f"Pedido #{orden.codigo_pedido} {accion} con éxito a {conductor.nombres}.",
                )
                return redirect("pedidos:lista_pedidos_admin")
        else:
            messages.error(request, "Por favor selecciona un conductor con vehículo asignado.")
            context = {"orden": orden, "conductores": conductores}
            return render(request, "pedidos/asignar_entrega.html", context)

    context = {"orden": orden, "conductores": conductores}
    return render(request, "pedidos/asignar_entrega.html", context)


@admin_required
def eliminar_orden(request, id):
    orden = get_object_or_404(Orden, codigo_pedido=id)
    order_id = orden.codigo_pedido
    db_alias = "remota" if debe_usar_bd_remota() else "default"

    try:
        with transaction.atomic(using=db_alias):

            if orden.estado not in (Orden.ENTREGADO, Orden.CANCELADO):
                revertir_stock_pedido(orden, request.user, "Eliminación", using=db_alias)
            liberar_vehiculo_pedido(orden)
    except DatabaseError as exc:
        logger.error("Error BD al limpiar pedido %s: %s", order_id, exc)
        messages.error(request, f"Error de base de datos: {exc}")
        return redirect("pedidos:lista_pedidos_admin")
    except Exception as exc:
        logger.error("Error limpiando pedido %s: %s", order_id, exc, exc_info=True)
        messages.error(request, f"Error al limpiar antes de eliminar: {exc}")
        return redirect("pedidos:lista_pedidos_admin")

    registrar_actividad(
        request, "eliminar", "pedidos", order_id,
        f"Pedido #{order_id} eliminado definitivamente por admin",
    )
    orden.delete()
    messages.success(request, f"Pedido #{order_id} eliminado correctamente.")
    return redirect("pedidos:lista_pedidos_admin")


# ========== Solicitudes (gestion_pedidos) ==========

@login_required
@transaction.atomic
def crear_pedido(request):
    materiales = MaterialConstruccion.objects.all()

    if request.method == "POST":
        materiales_ids = request.POST.getlist("materiales[]")
        cantidades = request.POST.getlist("cantidades[]")
        descuento = request.POST.get("descuento", 0)

        if not materiales_ids:
            messages.error(request, "Debe agregar al menos un material al pedido.")
            context = {"materiales": materiales}
            return render(request, "pedidos/crear_pedido.html", context)

        try:
            pedido = SolicitudPedido.objects.create(
                cliente=request.user, descuento=descuento, estado="pendiente"
            )

            for m_id, cant in zip(materiales_ids, cantidades, strict=False):
                cant = int(cant)
                material = get_object_or_404(MaterialConstruccion, pk=m_id)
                stock_obj = select_for_update_if_supported(Stock.objects, "default").get(material=material)

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

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error al procesar la solicitud: {str(e)}")

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
@transaction.atomic
def aprobar_pedido(request, pk):
    pedido = get_object_or_404(SolicitudPedido, pk=pk)
    if pedido.estado == "pendiente":
        pedido.estado = "aprobado"
        pedido.save()
        messages.success(request, f"Solicitud #{pedido.id} aprobada.")
    else:
        messages.warning(request, "Solo se pueden aprobar solicitudes en estado pendiente.")

    return redirect("pedidos:detalle_solicitud", pk=pk)


@admin_required
@transaction.atomic
def cancelar_pedido(request, pk):
    pedido = get_object_or_404(SolicitudPedido, pk=pk)
    if pedido.estado not in ["cancelado", "entregado"]:
        for detalle in pedido.detalles.all():
            stock_obj = select_for_update_if_supported(Stock.objects, "default").get(material=detalle.material)
            stock_obj.cantidad_actual += detalle.cantidad
            stock_obj.save()

        pedido.estado = "cancelado"
        pedido.save()
        messages.success(request, f"Solicitud #{pedido.id} cancelada y stock devuelto.")
    else:
        messages.warning(request, "Esta solicitud no puede ser cancelada.")

    return redirect("pedidos:detalle_solicitud", pk=pk)
