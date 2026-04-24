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
from apps.historial.utils import registrar_actividad

from apps.usuarios.views import admin_required

@admin_required
def reportes_admin(request):
    # Estadísticas de Órdenes
    ordenes = Orden.objects.all()
    total = ordenes.count()
    pendientes = ordenes.filter(estado="pendiente").count()
    en_ruta = ordenes.filter(estado="en_ruta").count()
    entregadas = ordenes.filter(estado="entregado").count()
    
    # Calcular porcentajes para la UI
    pct_pendientes = (pendientes * 100 / total) if total > 0 else 0
    pct_en_ruta = (en_ruta * 100 / total) if total > 0 else 0
    pct_entregadas = (entregadas * 100 / total) if total > 0 else 0

    # Materiales con stock crítico (< 10)
    stock_critico = Material.objects.filter(stock_info__cantidad__lt=10).select_related('stock_info')

    context = {
        # Resumen de Órdenes
        "total_ordenes": total,
        "pendientes": pendientes,
        "en_ruta": en_ruta,
        "entregadas": entregadas,
        "pct_pendientes": pct_pendientes,
        "pct_en_ruta": pct_en_ruta,
        "pct_entregadas": pct_entregadas,
        
        # Resumen de Usuarios
        "total_clientes": Usuario.objects.filter(rol="cliente").count(),
        "total_conductores": Usuario.objects.filter(rol="conductor").count(),
        
        # Resumen de Inventario y Vehículos
        "total_materiales": Material.objects.count(),
        "total_vehiculos": Vehiculo.objects.count(),
        
        # Financiero
        "total_ingresos": ordenes.aggregate(total=Sum("precio"))["total"] or 0,

        # Stock Crítico
        "stock_critico": stock_critico,
    }
    return render(request, "reportes/lista.html", context)

@admin_required
def exportar_reporte_pdf(request, tipo):
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
        for m in Material.objects.all().select_related('stock_info'):
            p = m.precio or 0
            precio_formateado = f"${int(p):,}".replace(",", ".")
            data.append([m.id, m.nombre, m.tipo, precio_formateado, m.stock])

    elif tipo == 'ventas':
        data.append(['ID', 'Cliente', 'Fecha', 'Total', 'Estado'])
        for o in Orden.objects.all():
            p = o.precio or 0
            precio_formateado = f"${int(p):,}".replace(",", ".")
            data.append([o.id, f"{o.cliente.usuario.nombres} {o.cliente.usuario.apellidos}", o.fecha.strftime('%Y-%m-%d'), precio_formateado, o.estado])

    elif tipo == 'pedidos':
        data.append(['ID', 'Cliente', 'Materiales', 'Total', 'Estado'])
        for o in Orden.objects.all().prefetch_related('detalles__material'):
            materiales = ", ".join([f"{d.cantidad}x {d.material.nombre}" for d in o.detalles.all()])
            p = o.precio or 0
            precio_formateado = f"${int(p):,}".replace(",", ".")
            data.append([o.id, f"{o.cliente.usuario.nombres} {o.cliente.usuario.apellidos}", materiales[:50] + "..." if len(materiales) > 50 else materiales, precio_formateado, o.estado])

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
