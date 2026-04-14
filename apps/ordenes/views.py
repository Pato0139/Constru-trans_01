from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from .models import Orden, Entrega
from apps.usuarios.models import Usuario, Vehiculo, Material
from historial.utils import registrar_actividad

def buscar_pedidos_admin(cliente_query=None, fecha_query=None, estado_query=None):
    """
    Lógica unificada para buscar pedidos por cliente, fecha o estado.
    """
    pedidos = Orden.objects.all().order_by("-fecha")
    
    if cliente_query:
        pedidos = pedidos.filter(
            Q(cliente__nombres__icontains=cliente_query) |
            Q(cliente__apellidos__icontains=cliente_query) |
            Q(cliente__documento__icontains=cliente_query)
        )
    
    if fecha_query:
        pedidos = pedidos.filter(fecha__date=fecha_query)

    if estado_query:
        pedidos = pedidos.filter(estado=estado_query)
        
    return pedidos

@login_required
def lista_pedidos_admin(request):
    cliente_query = request.GET.get('cliente')
    fecha_query = request.GET.get('fecha')
    estado_query = request.GET.get('estado')
    
    pedidos = buscar_pedidos_admin(cliente_query, fecha_query, estado_query)
        
    return render(request, "ordenes/lista.html", {
        "pedidos": pedidos,
        "cliente_query": cliente_query,
        "fecha_query": fecha_query,
        "estado_query": estado_query,
        "estados": Orden.ESTADOS
    })

@login_required
def ver_pedido_admin(request, id):
    orden = get_object_or_404(Orden, id=id)
    return render(request, "ordenes/detalle.html", {
        "orden": orden
    })

@login_required
def crear_entrega(request, orden_id):
    orden = get_object_or_404(Orden, id=orden_id)
    conductores = Usuario.objects.filter(rol="conductor")
    vehiculos = Vehiculo.objects.all()

    if request.method == "POST":
        conductor_id = request.POST.get("conductor")
        vehiculo_id = request.POST.get("vehiculo")

        if conductor_id and vehiculo_id:
            Entrega.objects.create(
                pedido=orden,
                conductor_id=conductor_id,
                vehiculo_id=vehiculo_id
            )

            orden.estado = "en_ruta"
            orden.conductor_id = conductor_id
            orden.fecha_toma_entrega = timezone.now()
            orden.save()

            registrar_actividad(request, 'editar', 'pedidos', orden.id, f"Pedido asignado a conductor ID: {conductor_id}")

            return redirect("ordenes:lista_pedidos_admin")
        else:
            return render(request, "ordenes/asignar_entrega.html", {
                "orden": orden,
                "conductores": conductores,
                "vehiculos": vehiculos,
                "error": "Por favor selecciona un conductor y un vehículo."
            })

    return render(request, "ordenes/asignar_entrega.html", {
        "orden": orden,
        "conductores": conductores,
        "vehiculos": vehiculos
    })

@login_required
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

    # Detalle de Materiales (Si la orden tiene materiales asociados, aquí los listaríamos)
    # Por ahora mostramos el total
    precio_formateado = f"${int(orden.total_pagar):,}".replace(",", ".")
    data = [
        ['Descripción', 'Total'],
        ['Servicio de Transporte y Materiales', precio_formateado]
    ]

    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t)
    
    elements.append(Spacer(1, 48))
    elements.append(Paragraph("Gracias por su compra.", styles['Italic']))

    doc.build(elements)
    
    registrar_actividad(request, 'otro', 'pedidos', orden.id, f"Factura descargada por {request.user.username}")
    
    return response

@login_required
def eliminar_orden(request, id):
    orden = get_object_or_404(Orden, id=id)
    registrar_actividad(request, 'eliminar', 'pedidos', id, f"Pedido eliminado de cliente: {orden.cliente}")
    orden.delete()
    return redirect("ordenes:lista_pedidos_admin")
