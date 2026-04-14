from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from apps.ordenes.models import Orden
from apps.usuarios.models import Usuario, Material, Vehiculo

from django.http import HttpResponse, JsonResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.utils.timezone import now
from historial.utils import registrar_actividad

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

@login_required
def reportes_pedidos(request):
    """
    GET /reportes/pedidos - Endpoint para obtener reportes de pedidos con filtros
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        tipo_filtro = request.GET.get('tipo', 'all')
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        
        ordenes = Orden.objects.all().order_by('-fecha')
        
        if tipo_filtro != 'all':
            ordenes = ordenes.filter(estado=tipo_filtro)
        
        if fecha_desde:
            ordenes = ordenes.filter(fecha__gte=fecha_desde)
        
        if fecha_hasta:
            ordenes = ordenes.filter(fecha__lte=fecha_hasta)
        
        data = {
            'total': ordenes.count(),
            'pendientes': ordenes.filter(estado='pendiente').count(),
            'en_ruta': ordenes.filter(estado='en_ruta').count(),
            'entregadas': ordenes.filter(estado='entregado').count(),
            'pedidos': [
                {
                    'id': o.id,
                    'cliente': f"{o.cliente.nombres} {o.cliente.apellidos}",
                    'fecha': o.fecha.strftime('%Y-%m-%d'),
                    'precio': f"${o.precio:,.0f}",
                    'estado': o.estado
                } for o in ordenes[:50]
            ]
        }
        return JsonResponse(data)
    
    return render(request, "reportes/pedidos.html")

@login_required
def reportes_admin(request):
    # Obtener el filtro de búsqueda
    search_query = request.GET.get('q', '')
    
    # Estadísticas de Órdenes
    ordenes = Orden.objects.all()
    
    # Datos de filtros
    clientes_data = Usuario.objects.filter(rol="cliente")
    materiales_data = Material.objects.all()
    ventas_data = Orden.objects.all()
    
    # Aplicar filtros de búsqueda
    if search_query:
        clientes_data = clientes_data.filter(
            Q(nombres__icontains=search_query) | 
            Q(apellidos__icontains=search_query) | 
            Q(user__email__icontains=search_query)
        )
        materiales_data = materiales_data.filter(
            Q(nombre__icontains=search_query) | 
            Q(tipo__icontains=search_query)
        )
        ventas_data = ventas_data.filter(
            Q(cliente__nombres__icontains=search_query) | 
            Q(cliente__apellidos__icontains=search_query)
        )
    
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
        "total_ingresos": ordenes.aggregate(total=Sum("precio"))["total"] or 0,
        
        # Datos filtrados
        "clientes_data": clientes_data,
        "materiales_data": materiales_data,
        "ventas_data": ventas_data,
        "search_query": search_query,
        "excel_available": EXCEL_AVAILABLE,
    }
    return render(request, "reportes/lista.html", context)

@login_required
def exportar_reporte(request, tipo, formato='pdf'):
    """
    Exportar reportes en PDF o Excel
    """
    if request.user.usuario.rol != 'admin':
        return HttpResponse("No autorizado", status=403)

    if formato == 'excel' and EXCEL_AVAILABLE:
        return exportar_reporte_excel(request, tipo)
    else:
        return exportar_reporte_pdf(request, tipo)

def exportar_reporte_excel(request, tipo):
    """
    Generar reporte en Excel
    """
    wb = Workbook()
    ws = wb.active
    
    # Valores por defecto
    titulo = f"Reporte de {tipo.replace('_', ' ').capitalize()}"
    ws.title = titulo[:31]
    
    # Estilos
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    
    # Título
    ws.append([titulo])
    ws['A1'].font = Font(bold=True, size=14)
    ws.append([f"Fecha de generación: {now().strftime('%Y-%m-%d %H:%M')}"])
    ws.append([])
    
    data = []
    if tipo == 'clientes':
        data.append(['ID', 'Nombre', 'Correo', 'Teléfono', 'Estado'])
        for u in Usuario.objects.filter(rol='cliente'):
            data.append([u.id, f"{u.nombres} {u.apellidos}", u.user.email, u.telefono, u.estado])
    
    elif tipo == 'materiales':
        data.append(['ID', 'Nombre', 'Tipo', 'Precio', 'Stock'])
        for m in Material.objects.all():
            data.append([m.id, m.nombre, m.tipo, m.precio, m.stock])

    elif tipo == 'ventas':
        data.append(['ID', 'Cliente', 'Fecha', 'Total', 'Estado'])
        for o in Orden.objects.all():
            data.append([o.id, f"{o.cliente.nombres} {o.cliente.apellidos}", o.fecha.strftime('%Y-%m-%d'), o.precio, o.estado])
    elif tipo == 'pedidos':
        data.append(['ID', 'Cliente', 'Fecha', 'Total', 'Estado'])
        for o in Orden.objects.all():
            data.append([o.id, f"{o.cliente.nombres} {o.cliente.apellidos}", o.fecha.strftime('%Y-%m-%d'), o.precio, o.estado])

    # Agregar datos
    for row_idx, row in enumerate(data, start=4):
        for col_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            if row_idx == 4:  # Header row
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center')

    # Ajustar ancho de columnas
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column_letter].width = min(max_length + 2, 50)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reporte_{tipo}_{now().strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    
    registrar_actividad(None, 'otro', 'reportes', None, f"Reporte de {tipo} exportado a Excel")
    
    return response

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
        for m in Material.objects.all():
            precio_formateado = f"${int(m.precio):,}".replace(",", ".")
            data.append([m.id, m.nombre, m.tipo, precio_formateado, m.stock])

    elif tipo == 'ventas':
        data.append(['ID', 'Cliente', 'Fecha', 'Total', 'Estado'])
        for o in Orden.objects.all():
            precio_formateado = f"${int(o.precio):,}".replace(",", ".")
            data.append([o.id, f"{o.cliente.nombres} {o.cliente.apellidos}", o.fecha.strftime('%Y-%m-%d'), precio_formateado, o.estado])
    elif tipo == 'pedidos':
        data.append(['ID', 'Cliente', 'Fecha', 'Total', 'Estado'])
        for o in Orden.objects.all():
            precio_formateado = f"${int(o.precio):,}".replace(",", ".")
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
