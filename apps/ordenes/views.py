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
    
    pedidos = buscar_pedidos_admin(cliente_query, fecha_query)
        
    return render(request, "ordenes/lista.html", {
        "pedidos": pedidos,
        "cliente_query": cliente_query,
        "fecha_query": fecha_query
    })

@admin_required
def ver_pedido_admin(request, id):
    orden = get_object_or_404(Orden, id=id)
    return render(request, "ordenes/detalle.html", {
        "orden": orden
    })

@admin_required
def crear_entrega(request, orden_id):
    orden = get_object_or_404(Orden, id=orden_id)
    # Solo conductores que tengan un vehículo asignado y estén disponibles
    conductores = Usuario.objects.filter(
        rol="conductor", 
        vehiculo_asignado__isnull=False,
        vehiculo_asignado__estado='disponible'
    )

    if request.method == "POST":
        conductor_id = request.POST.get("conductor")
        
        if conductor_id:
            conductor = get_object_or_404(Usuario, id=conductor_id)
            vehiculo = conductor.vehiculo_asignado
            
            Entrega.objects.create(
                pedido=orden,
                conductor=conductor,
                vehiculo=vehiculo,
                estado='en_ruta'
            )

            # Actualizar estado de la orden y el vehículo
            orden.estado = "en_ruta"
            orden.conductor = conductor
            orden.fecha_toma_entrega = timezone.now()
            orden.save()
            
            vehiculo.estado = 'en_ruta'
            vehiculo.save()

            registrar_actividad(request, 'editar', 'pedidos', orden.id, f"Pedido asignado a conductor: {conductor.nombres} con vehículo {vehiculo.placa}")
            messages.success(request, f"Pedido #{orden.id} asignado con éxito a {conductor.nombres}.")

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

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Encabezado Factura
    elements.append(Paragraph("FACTURA DE VENTA - CONSTRU-TRANS", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Número de Pedido: {orden.id}", styles['Normal']))
    elements.append(Paragraph(f"Fecha: {orden.fecha.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Paragraph(f"Cliente: {orden.cliente.nombres} {orden.cliente.apellidos}", styles['Normal']))
    elements.append(Spacer(1, 24))

    # Detalle de Materiales
    data = [['Material', 'Cantidad', 'Precio Unit.', 'Subtotal']]
    
    detalles = orden.detalles.all()
    if detalles.exists():
        for detalle in detalles:
            subtotal = detalle.cantidad * detalle.precio_unitario
            precio_u_f = f"${int(detalle.precio_unitario):,}".replace(",", ".")
            subtotal_f = f"${int(subtotal):,}".replace(",", ".")
            data.append([
                detalle.material.nombre,
                str(detalle.cantidad),
                precio_u_f,
                subtotal_f
            ])
    else:
        # Fallback si no hay detalles (orden antigua o error)
        precio_formateado = f"${int(orden.precio):,}".replace(",", ".")
        data.append(['Servicio General', '1', precio_formateado, precio_formateado])

    # Fila de Total
    total_f = f"${int(orden.precio):,}".replace(",", ".")
    data.append(['', '', 'TOTAL:', total_f])

    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('SPAN', (0, -1), (2, -1)), # Unir celdas para el total
    ]))
    elements.append(t)
    
    elements.append(Spacer(1, 48))
    elements.append(Paragraph("Gracias por su compra.", styles['Italic']))

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
                    
                    # Validar y descontar stock
                    stock_obj = Stock.objects.select_for_update().get(material=material)
                    if stock_obj.cantidad < cantidad:
                        raise ValueError(f"Stock insuficiente para {material.nombre}")

                    DetalleOrden.objects.create(
                        orden=nueva_orden,
                        material=material,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario
                    )
                    
                    # Descontar stock
                    stock_obj.cantidad = F('cantidad') - cantidad
                    stock_obj.save()
                    
                    # HU-18: Registrar movimiento de salida
                    MovimientoInventario.objects.create(
                        material=material,
                        tipo='salida',
                        cantidad=cantidad,
                        motivo=f"orden #{nueva_orden.id}",
                        referencia_id=nueva_orden.id,
                        usuario=request.user
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
