from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from .models import Orden, Entrega, DetalleOrden
from apps.usuarios.models import Usuario, Vehiculo, Material
from historial.utils import registrar_actividad
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

@login_required
def lista_pedidos_admin(request):
    pedidos = Orden.objects.all().order_by("-fecha")

    cliente_query = request.GET.get('cliente')
    fecha_query = request.GET.get('fecha')

    if cliente_query:
        pedidos = pedidos.filter(
            Q(cliente__nombres__icontains=cliente_query) |
            Q(cliente__apellidos__icontains=cliente_query)
        )

    if fecha_query:
        pedidos = pedidos.filter(fecha__date=fecha_query)

    return render(request, "ordenes/lista.html", {
        "pedidos": pedidos
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

    if request.user.usuario.rol != 'admin' and orden.cliente != request.user.usuario:
        return HttpResponse("No autorizado", status=403)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{orden.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("FACTURA DE VENTA - CONSTRU-TRANS", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Número de Pedido: {orden.id}", styles['Normal']))
    elements.append(Paragraph(f"Fecha: {orden.fecha.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Paragraph(f"Cliente: {orden.cliente.nombres} {orden.cliente.apellidos}", styles['Normal']))
    elements.append(Spacer(1, 24))

    data = [['Material', 'Cantidad', 'Precio Unit.', 'Subtotal']]
    for detalle in orden.detalles.all():
        data.append([
            detalle.material.nombre,
            str(detalle.cantidad),
            f"${detalle.precio_unitario}",
            f"${detalle.subtotal()}"
        ])

    if not orden.detalles.exists() and orden.material:
        data.append([
            orden.material.nombre,
            str(orden.cantidad),
            f"${orden.material.precio}",
            f"${orden.precio}"
        ])

    data.append(['', '', 'TOTAL', f"${orden.precio}"])

    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
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

@login_required
def api_total_orden(request, id):
    orden = get_object_or_404(Orden, id=id)
    detalles = []
    for detalle in orden.detalles.all():
        detalles.append({
            'material': detalle.material.nombre,
            'cantidad': detalle.cantidad,
            'precio_unitario': str(detalle.precio_unitario),
            'subtotal': str(detalle.subtotal()),
        })
    return JsonResponse({
        'orden_id': orden.id,
        'detalles': detalles,
        'total': str(orden.precio),
    })

@login_required
def agregar_material_pedido(request, id):
    orden = get_object_or_404(Orden, id=id)

    if orden.estado != Orden.PENDIENTE:
        return HttpResponse("Solo se pueden agregar materiales a pedidos pendientes.", status=400)

    if request.method == "POST":
        material_texto = request.POST.get("material_texto")
        cantidad = request.POST.get("cantidad")

        try:
            cantidad = int(float(cantidad))
        except (ValueError, TypeError):
            return HttpResponse("Cantidad inválida.", status=400)

        if cantidad <= 0:
            return HttpResponse("La cantidad debe ser mayor a 0.", status=400)

        material = Material.objects.filter(nombre__iexact=material_texto).first()

        if not material:
            material = Material.objects.create(
                nombre=material_texto,
                precio=0,
                stock=0
            )

        if material.stock == 0:
            return HttpResponse("El material no tiene stock disponible.", status=400)

        if cantidad > material.stock:
            return HttpResponse("La cantidad supera el stock disponible.", status=400)

        DetalleOrden.objects.create(
            orden=orden,
            material=material,
            cantidad=cantidad,
            precio_unitario=material.precio
        )

        material.stock -= cantidad
        material.save()

        registrar_actividad(
            request, 'editar', 'pedidos', orden.id,
            f"Material agregado: {material.nombre} x{cantidad}"
        )

        return redirect("ordenes:ver_pedido_admin", id=orden.id)

    return HttpResponse("Método no permitido.", status=405)

@login_required
def eliminar_material_pedido(request, id, detalle_id):
    orden = get_object_or_404(Orden, id=id)
    detalle = get_object_or_404(DetalleOrden, id=detalle_id, orden=orden)

    if orden.estado != Orden.PENDIENTE:
        return HttpResponse("Solo se pueden eliminar materiales de pedidos pendientes.", status=400)

    material = detalle.material
    material.stock += detalle.cantidad
    material.save()

    detalle.delete()

    registrar_actividad(
        request, 'editar', 'pedidos', orden.id,
        f"Material eliminado: {material.nombre}"
    )
    return redirect("ordenes:ver_pedido_admin", id=orden.id)