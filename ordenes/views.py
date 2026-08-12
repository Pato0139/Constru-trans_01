from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, DatabaseError
from django.db.models import F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
import logging

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from historial.utils import registrar_actividad
from inventario.models import MovimientoInventario
from pagos.models import PagoPedido
from pagos.services import registrar_estado_pago
from usuarios.models import Conductor, MaterialConstruccion, MetodoPago, Stock, Usuario
from usuarios.views import admin_required
from core.db_preference import debe_usar_bd_remota
from core.db_utils import select_for_update_if_supported

from .models import DetalleOrden, Entrega, Orden
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
    return redirect("ordenes:agregar_materiales", id=orden.codigo_pedido)


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
            return redirect("ordenes:agregar_materiales", id=orden.codigo_pedido)

        if cantidad < 1:
            messages.error(request, "La cantidad mínima es 1.")
            return redirect("ordenes:agregar_materiales", id=orden.codigo_pedido)

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

        return redirect("ordenes:agregar_materiales", id=orden.codigo_pedido)

    context = {"orden": orden, "materiales": materiales, "detalles": detalles}
    return render(request, "ordenes/agregar_materiales.html", context)

def buscar_pedidos_admin(cliente_query=None, fecha_query=None):
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
        )

    if fecha_query:
        pedidos = pedidos.filter(fecha_solicitud__date=fecha_query)

    return pedidos

@admin_required
def _render_lista_por_estado(request, estado, titulo):
    cliente_query = request.GET.get("cliente")
    fecha_query = request.GET.get("fecha")
    pedidos = buscar_pedidos_admin(cliente_query, fecha_query).filter(estado=estado)
    context = {
        "pedidos": pedidos,
        "cliente_query": cliente_query,
        "fecha_query": fecha_query,
        "titulo_panel": titulo,
    }
    return render(request, "ordenes/lista.html", context)


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
    if usuario_actual.rol == "cliente":
        if orden.cliente is None or orden.cliente.usuario_id != usuario_actual.id:
            messages.error(request, "No tienes permiso para ver este pedido.")
            return redirect("clientes:mis_pedidos")

    if request.method == "POST":
        if request.POST.get("accion_pago") == "registrar":
            metodo = request.POST.get("metodo_pago", "").strip()
            referencia = request.POST.get("referencia", "").strip()
            comprobante = request.FILES.get("comprobante")

            if not metodo:
                messages.error(request, "Selecciona un método de pago para continuar.")
                return redirect(f"{request.path}?tab=pagos")

            pago_pedido = orden.pagos_pedido.order_by("-fecha_creacion").first()
            if not pago_pedido:
                pago_pedido = PagoPedido.objects.create(
                    pedido=orden,
                    cliente=orden.cliente,
                    metodo_pago=metodo,
                    monto=orden.total or orden.precio or 0,
                    referencia=referencia,
                    estado_pago="contra_entrega" if metodo == "Contra entrega" else "pendiente",
                )
            else:
                pago_pedido.metodo_pago = metodo
                pago_pedido.referencia = referencia
                pago_pedido.monto = orden.total or orden.precio or 0

            if comprobante:
                pago_pedido.comprobante = comprobante
                pago_pedido.estado_pago = "en_revision"
            elif metodo == "Contra entrega":
                pago_pedido.estado_pago = "contra_entrega"
            else:
                pago_pedido.estado_pago = "pendiente"

            pago_pedido.save()
            pago_pedido.agregar_historial(
                f"Registro de pago enviado por {request.user.username} con método {metodo}."
            )
            messages.success(request, "Tu solicitud de pago quedó registrada. En breve será revisada.")
            return redirect(f"{request.path}?tab=pagos")

        if request.POST.get("accion_pago") in {"aprobar", "rechazar"}:
            pago_pedido = orden.pagos_pedido.order_by("-fecha_creacion").first()
            if not pago_pedido:
                messages.error(request, "Aún no existe un registro de pago para esta orden.")
                return redirect(f"{request.path}?tab=pagos")

            if request.POST.get("accion_pago") == "aprobar":
                registrar_estado_pago(pago_pedido, orden, "pago aprobado")
                pago_pedido.agregar_historial(f"Pago aprobado por {request.user.username}")
                pago_pedido.save(update_fields=["estado_pago", "motivo_rechazo", "fecha_actualizacion"])
                messages.success(request, f"Pago aprobado para el pedido #{orden.codigo_pedido}.")
            else:
                motivo = request.POST.get("motivo_rechazo", "").strip()
                if not motivo:
                    messages.error(request, "Escribe un motivo para rechazar el comprobante.")
                    return redirect(f"{request.path}?tab=pagos")
                pago_pedido.estado_pago = "pago rechazado"
                pago_pedido.motivo_rechazo = motivo
                pago_pedido.pedido.estado = Orden.CANCELADO
                pago_pedido.pedido.save(update_fields=["estado"])
                pago_pedido.agregar_historial(f"Pago rechazado por {request.user.username}: {motivo}")
                pago_pedido.save(update_fields=["estado_pago", "motivo_rechazo", "fecha_actualizacion"])
                messages.warning(request, "Pago rechazado y cliente notificado.")
            return redirect(f"{request.path}?tab=pagos")

        if usuario_actual.rol == "conductor":
            accion = request.POST.get("accion")
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

        elif usuario_actual.rol == "admin":
            if orden.estado == Orden.CANCELADO:
                messages.info(request, "El pedido está cancelado. Solo se permite su consulta.")
                return redirect("ordenes:ver_pedido_admin", id=orden.codigo_pedido)
            db_alias = "remota" if debe_usar_bd_remota() else "default"
            nuevo_estado = request.POST.get("estado")
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
                            return redirect("ordenes:ver_pedido_admin", id=orden.codigo_pedido)
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
                return redirect("ordenes:ver_pedido_admin", id=orden.codigo_pedido)

    pago_pedido = orden.pagos_pedido.order_by("-fecha_creacion").first()
    context = {
        "orden": orden,
        "metodos_pago": MetodoPago.objects.all(),
        "metodos_disponibles": [
            "Nequi",
            "Daviplata",
            "Bancolombia",
            "Contra entrega",
        ],
        "pago_pedido": pago_pedido,
        "cuentas_transferencia": {
            "Nequi": {
                "telefono": "300 123 4567",
                "titular": "ConstruTrans SAS",
                "documento": "900.123.456-1",
            },
            "Daviplata": {
                "telefono": "300 123 4567",
                "titular": "ConstruTrans SAS",
                "documento": "900.123.456-1",
            },
            "Bancolombia": {
                "numero": "0134 123 456 789",
                "titular": "ConstruTrans SAS",
                "tipo": "Cuenta corriente",
            },
        },
    }
    return render(request, "ordenes/detalle.html", context)


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
                    return render(request, "ordenes/asignar_entrega.html", context)

                if orden.conductor and orden.conductor != conductor:
                    vehiculo_anterior = orden.conductor.vehiculo_actual
                    if vehiculo_anterior:
                        vehiculo_anterior.estado = "disponible"
                        vehiculo_anterior.save()

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
                    # CORRECCIÓN #4: nunca pisar una entrega ya completada.
                    if entrega.estado == "entregado":
                        messages.warning(
                            request,
                            f"La entrega del pedido #{orden.codigo_pedido} ya fue marcada como entregada. "
                            "No se puede reasignar automáticamente.",
                        )
                        return redirect("ordenes:lista_pedidos_admin")

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
                return redirect("ordenes:lista_pedidos_admin")
        else:
            messages.error(request, "Por favor selecciona un conductor con vehículo asignado.")
            context = {"orden": orden, "conductores": conductores}
            return render(request, "ordenes/asignar_entrega.html", context)

    context = {"orden": orden, "conductores": conductores}
    return render(request, "ordenes/asignar_entrega.html", context)


@login_required
def descargar_factura(request, id):
    orden = get_object_or_404(Orden, codigo_pedido=id)
    usuario_actual = request.user


    if usuario_actual.rol != "admin":
        if orden.cliente is None or orden.cliente.usuario_id != usuario_actual.id:
            return HttpResponse("No autorizado", status=403)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="factura_{orden.codigo_pedido}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, topMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    color_gold = colors.Color(0.95, 0.61, 0.07)
    color_dark = colors.Color(0.07, 0.07, 0.07)
    color_accent = colors.Color(0.0, 0.34, 0.7)

    styles["Title"].fontSize = 22
    styles["Title"].textColor = color_accent
    styles["Title"].alignment = 0

    elements.append(Paragraph("CONSTRU-TRANS", styles["Title"]))
    elements.append(Paragraph("Suministros y Transporte de Construcción", styles["Italic"]))
    elements.append(Spacer(1, 10))
    elements.append(
        Table(
            [[""]],
            colWidths=[540],
            rowHeights=[2],
            style=[("BACKGROUND", (0, 0), (-1, -1), color_gold)],
        )
    )
    elements.append(Spacer(1, 20))


    cliente_nombre = "N/A"
    if orden.cliente is not None and getattr(orden.cliente, "usuario", None):
        cliente_nombre = f"{orden.cliente.usuario.nombres} {orden.cliente.usuario.apellidos}"

    info_data = [
        [
            Paragraph(f"<b>FACTURA:</b> #{orden.codigo_pedido}", styles["Normal"]),
            Paragraph(f"<b>CLIENTE:</b> {cliente_nombre}", styles["Normal"]),
        ],
        [
            Paragraph(f"<b>FECHA:</b> {orden.fecha.strftime('%d/%m/%Y %H:%M')}", styles["Normal"]),
            Paragraph(f"<b>DIRECCIÓN:</b> {orden.direccion_destino}", styles["Normal"]),
        ],
    ]
    info_table = Table(info_data, colWidths=[270, 270])
    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(info_table)
    elements.append(Spacer(1, 30))

    def format_money(val):
        try:
            v = float(val)
            rounded = int(round(v))
            s = str(rounded)
            parts = []
            while s:
                parts.append(s[-3:])
                s = s[:-3]
            return ".".join(reversed(parts))
        except (TypeError, ValueError):
            return "0"

    data = [["MATERIAL", "CANTIDAD", "PRECIO UNIT.", "SUBTOTAL"]]
    detalles = orden.detalles.all()
    if detalles.exists():
        for detalle in detalles:
            subtotal = detalle.cantidad * detalle.precio_unitario
            data.append(
                [
                    detalle.material.nombre.upper(),
                    str(detalle.cantidad),
                    format_money(detalle.precio_unitario),
                    format_money(subtotal),
                ]
            )
    else:
        data.append(["SERVICIO GENERAL", "1", format_money(orden.precio), format_money(orden.precio)])

    total_f = format_money(orden.precio)


    try:
        factura = orden.factura
        total_pagado = format_money(factura.total_pagado)
        por_pagar = format_money(factura.saldo_pendiente)
        nota_pago = ""
    except (AttributeError, Exception):
        total_pagado = "—"
        por_pagar = total_f
        nota_pago = " (factura aún no emitida)"

    data.append(["", "", "TOTAL:", total_f])
    data.append(["", "", "PAGADO:", total_pagado])
    data.append(["", "", f"POR PAGAR:{nota_pago}", por_pagar])

    t = Table(data, colWidths=[240, 80, 110, 110])
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), color_dark),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, 0), 12),
        ("GRID", (0, 0), (-1, -4) if len(data) > 5 else (-1, -2), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (2, -3), (3, -1), "Helvetica-Bold"),
        ("ALIGN", (2, -3), (3, -1), "RIGHT"),
        ("TEXTCOLOR", (2, -1), (3, -1), color_accent),
        ("FONTSIZE", (2, -1), (3, -1), 12),
    ]
    t.setStyle(TableStyle(table_style))
    elements.append(t)

    elements.append(Spacer(1, 50))
    notes_data = [
        [Paragraph("<b>NOTAS:</b>", styles["Normal"])],
        [Paragraph("1. Soporte legal de la transacción.", styles["Normal"])],
        [Paragraph("2. Materiales verificados en calidad y cantidad.", styles["Normal"])],
        [
            Paragraph(
                f"3. Estado actual del pedido: <b>{orden.get_estado_display().upper()}</b>",
                styles["Normal"],
            )
        ],
    ]
    notes_table = Table(notes_data, colWidths=[540])
    notes_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    elements.append(notes_table)

    elements.append(Spacer(1, 30))
    elements.append(Paragraph("¡Gracias por confiar en Constru-Trans!", styles["Italic"]))

    doc.build(elements)

    registrar_actividad(
        request, "otro", "pedidos", orden.codigo_pedido,
        f"Factura descargada por {request.user.username}",
    )
    return response


@admin_required
def eliminar_orden(request, id):
    orden = get_object_or_404(Orden, codigo_pedido=id)
    order_id = orden.codigo_pedido
    db_alias = "remota" if debe_usar_bd_remota() else "default"

    try:
        with transaction.atomic(using=db_alias):

            # Liberar vehículo SIEMPRE (idempotente).
            if orden.estado not in (Orden.ENTREGADO, Orden.CANCELADO):
                revertir_stock_pedido(orden, request.user, "Eliminación", using=db_alias)
            liberar_vehiculo_pedido(orden)
    except DatabaseError as exc:
        logger.error("Error BD al limpiar pedido %s: %s", order_id, exc)
        messages.error(request, f"Error de base de datos: {exc}")
        return redirect("ordenes:lista_pedidos_admin")
    except Exception as exc:
        logger.error("Error limpiando pedido %s: %s", order_id, exc, exc_info=True)
        messages.error(request, f"Error al limpiar antes de eliminar: {exc}")
        return redirect("ordenes:lista_pedidos_admin")

    registrar_actividad(
        request, "eliminar", "pedidos", order_id,
        f"Pedido #{order_id} eliminado definitivamente por admin",
    )
    orden.delete()
    messages.success(request, f"Pedido #{order_id} eliminado correctamente.")
    return redirect("ordenes:lista_pedidos_admin")
