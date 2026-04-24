from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, F
from django.db import transaction
from django.contrib import messages
from .models import Orden, Entrega, DetalleOrden
from apps.usuarios.models import Usuario, Vehiculo, Material, Stock
from apps.inventario.models import MovimientoInventario
from apps.historial.utils import registrar_actividad

def buscar_pedidos_admin(cliente_query=None, fecha_query=None):
    """
    Lógica unificada para buscar pedidos por cliente o fecha.
    """
    pedidos = Orden.objects.all().order_by("-fecha")
    
    if cliente_query:
        pedidos = pedidos.filter(
            Q(cliente__nombres__icontains=cliente_query) |
            Q(cliente__apellidos__icontains=cliente_query)
        )
    
    if fecha_query:
        pedidos = pedidos.filter(fecha__date=fecha_query)
        
    return pedidos

from apps.usuarios.views import admin_required

@admin_required
def lista_pedidos_admin(request):
    cliente_query = request.GET.get('cliente')
    fecha_query = request.GET.get('fecha')
    
    # Filtramos para mostrar solo pedidos pendientes (ventas por despachar)
    pedidos = buscar_pedidos_admin(cliente_query, fecha_query).filter(
        estado=Orden.PENDIENTE
    )
        
    return render(request, "ordenes/lista.html", {
        "pedidos": pedidos,
        "cliente_query": cliente_query,
        "fecha_query": fecha_query,
        "titulo_panel": "Ventas Pendientes"
    })

@admin_required
def lista_entregas_admin(request):
    cliente_query = request.GET.get('cliente')
    fecha_query = request.GET.get('fecha')
    
    # Filtramos para mostrar solo pedidos que están en ruta o entregados (logística)
    pedidos = buscar_pedidos_admin(cliente_query, fecha_query).filter(
        estado__in=[Orden.EN_RUTA, Orden.ENTREGADO]
    )
        
    return render(request, "ordenes/lista.html", {
        "pedidos": pedidos,
        "cliente_query": cliente_query,
        "fecha_query": fecha_query,
        "titulo_panel": "Control de Entregas"
    })

@login_required
def ver_pedido_admin(request, id):
    orden = get_object_or_404(Orden, id=id)
    # Si es cliente, solo puede ver sus propios pedidos
    if request.user.usuario.rol == 'cliente' and orden.cliente != request.user.usuario:
        messages.error(request, "No tienes permiso para ver este pedido.")
        return redirect("clientes:mis_pedidos")
    
    # Manejo de acciones (Conductor y Admin)
    if request.method == "POST":
        if request.user.usuario.rol == "conductor":
            accion = request.POST.get("accion")
            if accion == "confirmar":
                if orden.estado != Orden.ENTREGADO:
                    with transaction.atomic():
                        # Cambiar estado de la entrega
                        entrega = orden.entregas.filter(conductor=request.user.usuario).first()
                        if entrega:
                            entrega.estado = 'entregado'
                            entrega.save()
                            
                            # El signal actualizar_estado_orden se encargará de actualizar la Orden,
                            # descontar stock, crear factura y notificar a los admins.
                            
                            # Liberar el vehículo
                            if entrega.vehiculo:
                                entrega.vehiculo.estado = 'disponible'
                                entrega.vehiculo.save()
                            
                            registrar_actividad(request, 'confirmar_entrega', 'pedidos', orden.id, "Conductor confirmó entrega exitosa")
                            messages.success(request, f"¡Entrega del pedido #{orden.id} confirmada con éxito!")
                        else:
                            messages.error(request, "No tienes una entrega asignada para este pedido.")
                return redirect("usuarios:panel")
                
            elif accion == "cancelar":
                if orden.estado != Orden.ENTREGADO:
                    with transaction.atomic():
                        orden.estado = Orden.CANCELADO
                        orden.save()
                        
                        # Liberar el vehículo
                        entrega = orden.entregas.filter(conductor=request.user.usuario).first()
                        if entrega and entrega.vehiculo:
                            entrega.vehiculo.estado = 'disponible'
                            entrega.vehiculo.save()
                        
                        registrar_actividad(request, 'cancelar_entrega', 'pedidos', orden.id, "Conductor canceló la entrega")
                        messages.warning(request, f"Entrega del pedido #{orden.id} cancelada.")
                return redirect("usuarios:panel")
        
        elif request.user.usuario.rol == "admin":
            nuevo_estado = request.POST.get("estado")
            if nuevo_estado:
                with transaction.atomic():
                    # Si el admin lo marca como entregado manualmente
                    if nuevo_estado == "entregado" and orden.estado != "entregado":
                        # Buscamos la entrega asociada para marcarla como entregada
                        # Esto disparará el signal que descuenta stock y notifica
                        entrega = orden.entregas.first()
                        if entrega:
                            entrega.estado = 'entregado'
                            entrega.save()
                        else:
                            # Si no hay objeto Entrega (pedido manual), actualizamos directo
                            orden.estado = "entregado"
                            orden.fecha_entrega_real = timezone.now()
                            orden.save()
                    else:
                        # Si se marca como cancelado, liberar el vehículo si existe una entrega
                        if nuevo_estado == "cancelado":
                            entrega = orden.entregas.first()
                            if entrega and entrega.vehiculo:
                                entrega.vehiculo.estado = 'disponible'
                                entrega.vehiculo.save()
                                
                        orden.estado = nuevo_estado
                        if nuevo_estado == "en_ruta" and not orden.fecha_toma_entrega:
                            orden.fecha_toma_entrega = timezone.now()
                        orden.save()
                    
                    registrar_actividad(request, 'editar', 'pedidos', orden.id, f"Estado de pedido cambiado por admin a: {nuevo_estado}")
                    messages.success(request, f"Estado del pedido #{orden.id} actualizado a {nuevo_estado}.")
                return redirect("ordenes:ver_pedido_admin", id=orden.id)

    return render(request, "ordenes/detalle.html", {
        "orden": orden
    })

@admin_required
def crear_entrega(request, orden_id):
    orden = get_object_or_404(Orden, id=orden_id)
    # Mostramos todos los conductores activos
    # Filtrando solo por rol para que el admin vea a todos
    conductores = Usuario.objects.filter(rol="conductor")

    if request.method == "POST":
        conductor_id = request.POST.get("conductor")
        
        if conductor_id:
            with transaction.atomic():
                conductor = get_object_or_404(Usuario, id=conductor_id)
                vehiculo = conductor.vehiculo_asignado
                
                if not vehiculo:
                    messages.error(request, f"El conductor {conductor.nombres} no tiene un vehículo asignado. Por favor, asígnale uno en la gestión de usuarios.")
                    return render(request, "ordenes/asignar_entrega.html", {
                        "orden": orden,
                        "conductores": conductores,
                    })

                # Si ya existe una entrega para este pedido, liberamos el vehículo anterior si cambió
                if orden.conductor and orden.conductor != conductor:
                    vehiculo_anterior = orden.conductor.vehiculo_asignado
                    if vehiculo_anterior:
                        vehiculo_anterior.estado = 'disponible'
                        vehiculo_anterior.save()

                # Crear o actualizar registro de entrega
                entrega, created = Entrega.objects.get_or_create(
                    pedido=orden,
                    defaults={
                        'conductor': conductor,
                        'vehiculo': vehiculo,
                        'estado': 'en_ruta'
                    }
                )
                
                if not created:
                    entrega.conductor = conductor
                    entrega.vehiculo = vehiculo
                    entrega.estado = 'en_ruta'
                    entrega.save()

                # Actualizar estado de la orden y el vehículo
                orden.estado = "en_ruta"
                orden.conductor = conductor
                if not orden.fecha_toma_entrega:
                    orden.fecha_toma_entrega = timezone.now()
                orden.save()
                
                vehiculo.estado = 'en_ruta'
                vehiculo.save()

                accion = "reasignado" if not created else "asignado"
                registrar_actividad(request, 'editar', 'pedidos', orden.id, f"Pedido {accion} a conductor: {conductor.nombres} con vehículo {vehiculo.placa}")
                messages.success(request, f"Pedido #{orden.id} {accion} con éxito a {conductor.nombres}.")

                return redirect("ordenes:lista_pedidos_admin")
        else:
            messages.error(request, "Por favor selecciona un conductor con vehículo asignado.")
            return render(request, "ordenes/asignar_entrega.html", {
                "orden": orden,
                "conductores": conductores,
            })

    return render(request, "ordenes/asignar_entrega.html", {
        "orden": orden,
        "conductores": conductores,
    })

@admin_required
def editar_orden(request, id):
    orden = get_object_or_404(Orden, id=id)
    if request.method == "POST":
        nuevo_estado = request.POST.get("estado")
        
        if nuevo_estado == "en_ruta" and orden.estado != "en_ruta":
            orden.fecha_toma_entrega = timezone.now()
        elif nuevo_estado == "entregado" and orden.estado != "entregado":
            orden.fecha_entrega_real = timezone.now()
            
        orden.estado = nuevo_estado
        orden.save()
        registrar_actividad(request, 'editar', 'pedidos', orden.id, f"Estado de pedido cambiado a: {nuevo_estado}")
        messages.success(request, f"Estado del pedido #{orden.id} actualizado a {nuevo_estado}.")
        return redirect("ordenes:lista_pedidos_admin")
    return render(request, "ordenes/detalle.html", {"orden": orden})

@login_required
def descargar_factura(request, id):
    orden = get_object_or_404(Orden, id=id)
    
    # Solo el cliente dueño del pedido o un admin pueden descargarla
    if request.user.usuario.rol != 'admin' and orden.cliente != request.user.usuario:
        return HttpResponse("No autorizado", status=403)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{orden.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, topMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    # Colores Premium
    color_gold = colors.Color(0.95, 0.61, 0.07) # #F39C12
    color_dark = colors.Color(0.07, 0.07, 0.07) # #121212
    color_accent = colors.Color(0.0, 0.34, 0.7) # #0056B3

    # Estilos personalizados
    styles['Title'].fontSize = 22
    styles['Title'].textColor = color_accent
    styles['Title'].alignment = 0 # Left
    
    # Encabezado con Diseño
    elements.append(Paragraph("CONSTRU-TRANS", styles['Title']))
    elements.append(Paragraph("Suministros y Transporte de Construcción", styles['Italic']))
    elements.append(Spacer(1, 10))
    
    # Línea decorativa
    elements.append(Table([['']], colWidths=[540], rowHeights=[2], style=[('BACKGROUND', (0,0), (-1,-1), color_gold)]))
    elements.append(Spacer(1, 20))

    # Información de Factura y Cliente (Tabla de 2 columnas)
    info_data = [
        [Paragraph(f"<b>FACTURA:</b> #{orden.id}", styles['Normal']), 
         Paragraph(f"<b>CLIENTE:</b> {orden.cliente.usuario.nombres} {orden.cliente.usuario.apellidos}", styles['Normal'])],
        [Paragraph(f"<b>FECHA:</b> {orden.fecha.strftime('%d/%m/%Y %H:%M')}", styles['Normal']),
         Paragraph(f"<b>DIRECCIÓN:</b> {orden.direccion_destino}", styles['Normal'])]
    ]
    info_table = Table(info_data, colWidths=[270, 270])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 30))

    # Detalle de Materiales
    data = [['MATERIAL', 'CANTIDAD', 'PRECIO UNIT.', 'SUBTOTAL']]
    
    detalles = orden.detalles.all()
    if detalles.exists():
        for detalle in detalles:
            subtotal = detalle.cantidad * detalle.precio_unitario
            precio_u_f = f"${int(detalle.precio_unitario):,}".replace(",", ".")
            subtotal_f = f"${int(subtotal):,}".replace(",", ".")
            data.append([
                detalle.material.nombre.upper(),
                str(detalle.cantidad),
                precio_u_f,
                subtotal_f
            ])
    else:
        precio_formateado = f"${int(orden.precio):,}".replace(",", ".")
        data.append(['SERVICIO GENERAL', '1', precio_formateado, precio_formateado])

    # Filas de Totales
    total_f = f"${int(orden.precio):,}".replace(",", ".")
    
    # Obtener información de pagos si existe factura asociada
    try:
        factura = orden.factura
        total_pagado = f"${int(factura.total_pagado):,}".replace(",", ".")
        por_pagar = f"${int(factura.saldo_pendiente):,}".replace(",", ".")
    except:
        total_pagado = "$0"
        por_pagar = total_f

    data.append(['', '', 'TOTAL:', total_f])
    data.append(['', '', 'PAGADO:', total_pagado])
    data.append(['', '', 'POR PAGAR:', por_pagar])

    t = Table(data, colWidths=[240, 80, 110, 110])
    
    # Estilo de la Tabla Detalle
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), color_dark),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -4) if len(data) > 5 else (-1, -2), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Estilo para las filas de totales
        ('FONTNAME', (2, -3), (3, -1), 'Helvetica-Bold'),
        ('ALIGN', (2, -3), (3, -1), 'RIGHT'),
        ('TEXTCOLOR', (2, -1), (3, -1), color_accent),
        ('FONTSIZE', (2, -1), (3, -1), 12),
    ]
    
    t.setStyle(TableStyle(table_style))
    elements.append(t)
    
    elements.append(Spacer(1, 50))
    
    # Pie de página / Notas
    notes_data = [
        [Paragraph("<b>NOTAS:</b>", styles['Normal'])],
        [Paragraph("1. Esta factura es un soporte legal de la transacción realizada.", styles['Normal'])],
        [Paragraph("2. Los materiales entregados han sido verificados en calidad y cantidad.", styles['Normal'])],
        [Paragraph(f"3. Estado actual del pedido: <b>{orden.get_estado_display().upper()}</b>", styles['Normal'])]
    ]
    notes_table = Table(notes_data, colWidths=[540])
    notes_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(notes_table)
    
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("¡Gracias por confiar en Constru-Trans!", styles['Italic']))

    doc.build(elements)
    
    registrar_actividad(request, 'otro', 'pedidos', orden.id, f"Factura descargada por {request.user.username}")
    
    return response

@admin_required
def eliminar_orden(request, id):
    orden = get_object_or_404(Orden, id=id)
    order_id = orden.id
    registrar_actividad(request, 'eliminar', 'pedidos', id, f"Pedido eliminado de cliente: {orden.cliente}")
    orden.delete()
    messages.success(request, f"Pedido #{order_id} eliminado correctamente.")
    return redirect("ordenes:lista_pedidos_admin")

@login_required
def crear_pedido(request):
    materiales = Material.objects.all()
    if request.method == "POST":
        materiales_ids = request.POST.getlist('material_id[]')
        cantidades = request.POST.getlist('cantidad[]')
        direccion = request.POST.get("direccion")
        fecha_entrega = request.POST.get("fecha_entrega")

        if not materiales_ids or not direccion:
            messages.error(request, "Por favor selecciona al menos un material y una dirección.")
            return render(request, "clientes/form.html", {"materiales": materiales, "action": "crear"})

        try:
            with transaction.atomic():
                nueva_orden = Orden.objects.create(
                    cliente=request.user.usuario,
                    direccion_destino=direccion,
                    fecha_entrega_programada=fecha_entrega if fecha_entrega else None,
                    estado='pendiente'
                )

                total_general = 0
                for m_id, cant in zip(materiales_ids, cantidades):
                    material = get_object_or_404(Material, id=m_id)
                    cantidad = int(cant)
                    precio_unitario = material.precio
                    
                    # Validar stock (pero no descontar aún, se hará al entregar)
                    stock_obj = Stock.objects.get(material=material)
                    if stock_obj.cantidad < cantidad:
                        raise ValueError(f"Stock insuficiente para {material.nombre}")

                    DetalleOrden.objects.create(
                        orden=nueva_orden,
                        material=material,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario
                    )
                    
                    total_general += precio_unitario * cantidad

                nueva_orden.precio = total_general
                nueva_orden.save()

            messages.success(request, f"Pedido #{nueva_orden.id} creado con éxito.")
            return redirect("clientes:mis_pedidos")

        except Exception as e:
            messages.error(request, f"Error al crear el pedido: {str(e)}")
            
    return render(request, "clientes/form.html", {
        "materiales": materiales,
        "action": "crear"
    })
