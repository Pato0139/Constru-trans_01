from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from historial.utils import registrar_actividad
from inventario.models import MovimientoInventario
from usuarios.models import MaterialConstruccion, MetodoPago, Stock, Usuario
from usuarios.views import admin_required
from core.db_preference import debe_usar_bd_remota

from .models import DetalleOrden, Entrega, Orden
from .utils import liberar_vehiculo_pedido, revertir_stock_pedido


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
                Stock.objects.select_for_update().using(db_alias).get(material=detalle.material)
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
        cantidad = float(request.POST.get("cantidad", 0))

        if material_id and cantidad > 0:
            material = get_object_or_404(MaterialConstruccion, pk=material_id)
            stock_obj = Stock.objects.get(material=material)

            if stock_obj.cantidad_actual >= cantidad:
                with transaction.atomic():
                    # Crear o actualizar detalle
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

                    # Descontar stock
                    stock_obj.cantidad_actual = F("cantidad_actual") - cantidad
                    stock_obj.save()

                    # Registrar movimiento
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
    """
    Lógica unificada para buscar pedidos por cliente o fecha.
    Optimizado con select_related para evitar N+1.
    """
    pedidos = (
        Orden.objects.all()
        .select_related("usuario", "cliente", "conductor")
        .prefetch_related("detalles__material", "entregas")
        .order_by("-fecha")
    )

    if cliente_query:
        pedidos = pedidos.filter(
            Q(cliente__nombres__icontains=cliente_query)
            | Q(cliente__apellidos__icontains=cliente_query)
        )

    if fecha_query:
        pedidos = pedidos.filter(fecha__date=fecha_query)

    return pedidos


@admin_required
def lista_pedidos_admin(request):
    cliente_query = request.GET.get("cliente")
    fecha_query = request.GET.get("fecha")

    # Filtramos para mostrar solo pedidos pendientes (ventas por despachar)
    pedidos = buscar_pedidos_admin(cliente_query, fecha_query).filter(estado=Orden.PENDIENTE)

    context = {
        "pedidos": pedidos,
        "cliente_query": cliente_query,
        "fecha_query": fecha_query,
        "titulo_panel": "Ventas Pendientes",
    }

    return render(request, "ordenes/lista.html", context)


@admin_required
def lista_entregas_admin(request):
    cliente_query = request.GET.get("cliente")
    fecha_query = request.GET.get("fecha")

    # Filtro para mostrar solo pedidos
    pedidos = buscar_pedidos_admin(cliente_query, fecha_query).filter(estado=Orden.EN_RUTA)

    context = {
        "pedidos": pedidos,
        "cliente_query": cliente_query,
        "fecha_query": fecha_query,
        "titulo_panel": "Control de Entregas",
    }

    return render(request, "ordenes/lista.html", context)


@login_required
def ver_pedido_admin(request, id):
    orden = get_object_or_404(Orden, codigo_pedido=id)
    if request.user.usuario.rol == "cliente" and (
        orden.cliente is None or orden.cliente.usuario_id != request.user.usuario.id
    ):
        messages.error(request, "No tienes permiso para ver este pedido.")
        return redirect("clientes:mis_pedidos")

    # Manejo de acciones
    if request.method == "POST":
        if request.user.usuario.rol == "conductor":
            accion = request.POST.get("accion")
            if accion == "confirmar":
                if orden.estado != Orden.ENTREGADO:
                    with transaction.atomic():
                        # Cambiar estado de la entrega
                        entrega = orden.entregas.filter(conductor=request.user.usuario).first()
                        if entrega:
                            entrega.estado = "entregado"
                            entrega.save()

                            # Liberar el vehículo
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
                if orden.estado != Orden.ENTREGADO and orden.estado != Orden.CANCELADO:
                    db_alias = "remota" if debe_usar_bd_remota() else "default"
                    with transaction.atomic():
                        with transaction.atomic(using=db_alias):
                            # Liberar el vehículo
                            liberar_vehiculo_pedido(orden)

                            # Revertir stock usando utilidad
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

        elif request.user.usuario.rol == "admin":
            db_alias = "remota" if debe_usar_bd_remota() else "default"
            nuevo_estado = request.POST.get("estado")
            if nuevo_estado:
                with transaction.atomic():
                    if nuevo_estado == "entregado" and orden.estado != "entregado":
                        entrega = orden.entregas.first()
                        if entrega:
                            entrega.estado = "entregado"
                            entrega.save()
                        else:
                            orden.estado = "entregado"
                            orden.fecha_entrega_real = timezone.now()
                            orden.save()
                    else:
                        if nuevo_estado == "cancelado" and orden.estado != "cancelado":
                            with transaction.atomic(using=db_alias):
                                liberar_vehiculo_pedido(orden)
                                revertir_stock_pedido(
                                    orden, request.user, "Cancelación (Admin)", using=db_alias
                                )

                        orden.estado = nuevo_estado
                        if nuevo_estado == "en_ruta" and not orden.fecha_toma_entrega:
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

    context = {"orden": orden, "metodos_pago": MetodoPago.objects.all()}

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
                        f"El conductor {conductor.nombres} no tiene un vehículo asignado. Por favor, asígnale uno en la gestión de usuarios.",
                    )
                    context = {
                        "orden": orden,
                        "conductores": conductores,
                    }

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
                    entrega.conductor = conductor
                    entrega.vehiculo = vehiculo
                    entrega.estado = "en_ruta"
                    entrega.direccion_entrega = orden.direccion_destino
                    entrega.save()

                orden.estado = "en_ruta"
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
            context = {
                "orden": orden,
                "conductores": conductores,
            }

            return render(request, "ordenes/asignar_entrega.html", context)

    context = {
        "orden": orden,
        "conductores": conductores,
    }

    return render(request, "ordenes/asignar_entrega.html", context)


@login_required
def descargar_factura(request, id):
    orden = get_object_or_404(Orden, codigo_pedido=id)
    if request.user.usuario.rol != "admin" and orden.cliente.usuario != request.user.usuario:
        return HttpResponse("No autorizado", status=403)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="factura_{orden.codigo_pedido}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, topMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    color_gold = colors.Color(0.95, 0.61, 0.07)  # #F39C12
    color_dark = colors.Color(0.07, 0.07, 0.07)  # #121212
    color_accent = colors.Color(0.0, 0.34, 0.7)  # #0056B3

    styles["Title"].fontSize = 22
    styles["Title"].textColor = color_accent
    styles["Title"].alignment = 0  # Left

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

    info_data = [
        [
            Paragraph(f"<b>FACTURA:</b> #{orden.codigo_pedido}", styles["Normal"]),
            Paragraph(
                f"<b>CLIENTE:</b> {orden.cliente.usuario.nombres} {orden.cliente.usuario.apellidos}",
                styles["Normal"],
            ),
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
        except Exception:
            return "0"

    # Detalle de Materiales
    data = [["MATERIAL", "CANTIDAD", "PRECIO UNIT.", "SUBTOTAL"]]

    detalles = orden.detalles.all()
    if detalles.exists():
        for detalle in detalles:
            subtotal = detalle.cantidad * detalle.precio_unitario
            precio_u_f = format_money(detalle.precio_unitario)
            subtotal_f = format_money(subtotal)
            data.append(
                [detalle.material.nombre.upper(), str(detalle.cantidad), precio_u_f, subtotal_f]
            )
    else:
        precio_formateado = format_money(orden.precio)
        data.append(["SERVICIO GENERAL", "1", precio_formateado, precio_formateado])

    # Filas de Totales
    total_f = format_money(orden.precio)

    try:
        factura = orden.factura
        total_pagado = format_money(factura.total_pagado)
        por_pagar = format_money(factura.saldo_pendiente)
    except Exception:
        total_pagado = "0"
        por_pagar = total_f

    data.append(["", "", "TOTAL:", total_f])
    data.append(["", "", "PAGADO:", total_pagado])
    data.append(["", "", "POR PAGAR:", por_pagar])

    t = Table(data, colWidths=[240, 80, 110, 110])

    # Estilo de la Tabla Detalle
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
        # Estilo para las filas de totales
        ("FONTNAME", (2, -3), (3, -1), "Helvetica-Bold"),
        ("ALIGN", (2, -3), (3, -1), "RIGHT"),
        ("TEXTCOLOR", (2, -1), (3, -1), color_accent),
        ("FONTSIZE", (2, -1), (3, -1), 12),
    ]

    t.setStyle(TableStyle(table_style))
    elements.append(t)

    elements.append(Spacer(1, 50))

    # Pie de página / Notas
    notes_data = [
        [Paragraph("<b>NOTAS:</b>", styles["Normal"])],
        [
            Paragraph(
                "1. Esta factura es un soporte legal de la transacción realizada.", styles["Normal"]
            )
        ],
        [
            Paragraph(
                "2. Los materiales entregados han sido verificados en calidad y cantidad.",
                styles["Normal"],
            )
        ],
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
        request,
        "otro",
        "pedidos",
        orden.codigo_pedido,
        f"Factura descargada por {request.user.username}",
    )

    return response


@admin_required
def eliminar_orden(request, id):
    orden = get_object_or_404(Orden, codigo_pedido=id)
    order_id = orden.codigo_pedido

    if orden.estado not in ["entregado", "cancelado"]:
        db_alias = "remota" if debe_usar_bd_remota() else "default"
        try:
            with transaction.atomic(using=db_alias):
                revertir_stock_pedido(orden, request.user, "Eliminación", using=db_alias)
        except Exception as e:
            messages.error(request, f"Error al devolver stock: {e}")
            return redirect("ordenes:lista_pedidos_admin")

    registrar_actividad(
        request,
        "eliminar",
        "pedidos",
        order_id,
        f"Pedido #{order_id} eliminado definitivamente por admin",
    )
    orden.delete()
    messages.success(request, f"Pedido #{order_id} eliminado correctamente.")
    return redirect("ordenes:lista_pedidos_admin")
