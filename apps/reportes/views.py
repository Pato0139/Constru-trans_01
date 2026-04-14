from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from apps.ordenes.models import Orden
from apps.usuarios.models import Usuario, Material, Vehiculo

from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.utils.timezone import now
from historial.utils import registrar_actividad

@login_required
def reportes_admin(request):
    try:
        # Estadísticas de Órdenes
        ordenes = Orden.objects.all()
        context = {
            # Resumen de Órdenes
            "total_ordenes": ordenes.count(),
            "pendientes": ordenes.filter(estado="pendiente").count(),
            "en_ruta": ordenes.filter(estado="en_ruta").count(),
            "entregadas": ordenes.filter(estado="entregado").count(),
            
            # Resumen de Usuarios
            "total_clientes": Usuario.objects.filter(rol="cliente").count(),
            "total_conductores": Usuario.objects.filter(rol="conductor").count(),
            
            # Resumen de Inventario y Vehículos
            "total_materiales": Material.objects.count(),
            "total_vehiculos": Vehiculo.objects.count(),
            
            # Financiero
            "total_ingresos": ordenes.aggregate(total=Sum("total_pagar"))["total"] or 0,
            "now": now(),
        }
    except Exception as e:
        registrar_actividad(request, 'error', 'reportes', None, f"Error al generar dashboard de reportes: {str(e)}")
        context = {
            "total_ordenes": 0, "pendientes": 0, "en_ruta": 0, "entregadas": 0,
            "total_clientes": 0, "total_conductores": 0, "total_materiales": 0, "total_vehiculos": 0,
            "total_ingresos": 0, "now": now()
        }
    
    return render(request, "reportes/lista.html", context)

@login_required
def exportar_reporte_pdf(request, tipo):
    if request.user.usuario.rol != 'admin':
        return HttpResponse("No autorizado", status=403)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_{tipo}_{now().strftime("%Y%m%d")}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Título
    titulo = f"Reporte de {tipo.replace('_', ' ').capitalize()}"
    elements.append(Paragraph(titulo, styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Fecha de generación: {now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 24))

    data = []
    if tipo == 'clientes':
        data.append(['ID', 'Nombre', 'Correo', 'Teléfono', 'Estado'])
        for u in Usuario.objects.filter(rol='cliente'):
            data.append([u.id, f"{u.nombres} {u.apellidos}", u.user.email, u.telefono, u.estado])
    
    elif tipo == 'materiales':
        data.append(['ID', 'Nombre', 'Tipo', 'Precio', 'Stock'])
        for m in Material.objects.all().select_related('stock'):
            precio_formateado = f"${int(m.precio):,}".replace(",", ".")
            stock_actual = m.stock.cantidad_actual if hasattr(m, 'stock') else 0
            data.append([m.id, m.nombre, m.tipo, precio_formateado, stock_actual])

    elif tipo == 'ventas':
        data.append(['ID', 'Cliente', 'Fecha', 'Total', 'Estado'])
        for o in Orden.objects.all():
            precio_formateado = f"${int(o.total_pagar):,}".replace(",", ".")
            data.append([o.id, f"{o.cliente.nombres} {o.cliente.apellidos}", o.fecha.strftime('%Y-%m-%d'), precio_formateado, o.estado])

    # Estilo de la tabla
    if data:
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("No hay datos disponibles para este reporte.", styles['Normal']))

    doc.build(elements)
    
    registrar_actividad(request, 'otro', 'reportes', None, f"Reporte de {tipo} exportado a PDF")
    
    return response
