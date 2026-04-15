from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Count
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
from datetime import datetime, timedelta
import json

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
    
    # Solicitud AJAX para gráficas de ventas
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return generar_datos_graficas_admin(request)
    
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
        
        # Resumen de Ventas
        "total_ventas": ventas_data.count(),
        "ingresos_totales": ventas_data.aggregate(total=Sum('precio'))['total'] or 0,
        "promedio_venta": ventas_data.aggregate(promedio=Sum('precio') / Count('id'))['promedio'] or 0 if ventas_data.exists() else 0,
        "ventas_entregadas": ventas_data.filter(estado='entregado').count(),
        "ventas_pendientes": ventas_data.filter(estado='pendiente').count(),
        "ventas_en_ruta": ventas_data.filter(estado='en_ruta').count(),
        "ventas_canceladas": ventas_data.filter(estado='cancelado').count(),
        
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

def generar_datos_graficas_admin(request):
    """
    Genera datos JSON para gráficas de ventas en el admin
    """
    ventas = Orden.objects.all().order_by('-fecha')
    
    # Gráfica 1: Ventas por estado
    ventas_por_estado = {
        'Pendiente': ventas.filter(estado='pendiente').count(),
        'En Ruta': ventas.filter(estado='en_ruta').count(),
        'Entregado': ventas.filter(estado='entregado').count(),
        'Cancelado': ventas.filter(estado='cancelado').count(),
    }
    
    # Gráfica 2: Ingresos por estado
    ingresos_por_estado = {
        'Pendiente': float(ventas.filter(estado='pendiente').aggregate(total=Sum('precio'))['total'] or 0),
        'En Ruta': float(ventas.filter(estado='en_ruta').aggregate(total=Sum('precio'))['total'] or 0),
        'Entregado': float(ventas.filter(estado='entregado').aggregate(total=Sum('precio'))['total'] or 0),
        'Cancelado': float(ventas.filter(estado='cancelado').aggregate(total=Sum('precio'))['total'] or 0),
    }
    
    # Gráfica 3: Top clientes
    top_clientes = ventas.values('cliente__nombres', 'cliente__apellidos').annotate(
        count=Count('id'),
        total=Sum('precio')
    ).order_by('-count')[:10]
    
    clientes_labels = [f"{c['cliente__nombres']} {c['cliente__apellidos']}" for c in top_clientes]
    clientes_data = [c['count'] for c in top_clientes]
    clientes_ingresos = [float(c['total'] or 0) for c in top_clientes]
    
    # Gráfica 4: Ventas por material
    ventas_por_material = ventas.values('material__nombre').annotate(
        count=Count('id'),
        total=Sum('precio')
    ).order_by('-count')[:10]
    
    material_labels = [m['material__nombre'] or 'Sin material' for m in ventas_por_material]
    material_data = [m['count'] for m in ventas_por_material]
    material_ingresos = [float(m['total'] or 0) for m in ventas_por_material]
    
    data = {
        'ventas_por_estado': {
            'labels': list(ventas_por_estado.keys()),
            'data': list(ventas_por_estado.values()),
        },
        'ingresos_por_estado': {
            'labels': list(ingresos_por_estado.keys()),
            'data': list(ingresos_por_estado.values()),
        },
        'top_clientes_compras': {
            'labels': clientes_labels,
            'data': clientes_data,
            'ingresos': clientes_ingresos,
        },
        'ventas_por_material': {
            'labels': material_labels,
            'data': material_data,
            'ingresos': material_ingresos,
        }
    }
    
    return JsonResponse(data)

@login_required
def reportes_ventas(request):
    """
    GET /reportes/ventas - Endpoint para obtener reportes de ventas con gráficas
    """
    # Obtener filtros de fechas
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    # Obtener todas las órdenes (ventas)
    ventas = Orden.objects.all().order_by('-fecha')
    
    # Aplicar filtros de fechas
    if fecha_desde:
        ventas = ventas.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        ventas = ventas.filter(fecha__lte=fecha_hasta)
    
    # Solicitud AJAX para datos de gráficas
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return generar_datos_graficas(ventas, request)
    
    # Contexto para el template
    context = {
        'total_ventas': ventas.count(),
        'ingresos_totales': ventas.aggregate(total=Sum('precio'))['total'] or 0,
        'promedio_venta': ventas.aggregate(promedio=Sum('precio') / Count('id'))['promedio'] or 0 if ventas.exists() else 0,
        'ventas_entregadas': ventas.filter(estado='entregado').count(),
        'ventas_pendientes': ventas.filter(estado='pendiente').count(),
        'ventas_en_ruta': ventas.filter(estado='en_ruta').count(),
        'ventas_canceladas': ventas.filter(estado='cancelado').count(),
    }
    
    return render(request, "reportes/ventas.html", context)

def generar_datos_graficas(ventas, request):
    """
    Genera datos JSON para las gráficas
    """
    # Gráfica 1: Ventas por estado
    ventas_por_estado = {
        'Pendiente': ventas.filter(estado='pendiente').count(),
        'En Ruta': ventas.filter(estado='en_ruta').count(),
        'Entregado': ventas.filter(estado='entregado').count(),
        'Cancelado': ventas.filter(estado='cancelado').count(),
    }
    
    # Gráfica 2: Ingresos por estado
    ingresos_por_estado = {
        'Pendiente': float(ventas.filter(estado='pendiente').aggregate(total=Sum('precio'))['total'] or 0),
        'En Ruta': float(ventas.filter(estado='en_ruta').aggregate(total=Sum('precio'))['total'] or 0),
        'Entregado': float(ventas.filter(estado='entregado').aggregate(total=Sum('precio'))['total'] or 0),
        'Cancelado': float(ventas.filter(estado='cancelado').aggregate(total=Sum('precio'))['total'] or 0),
    }
    
    # Gráfica 3: Top clientes por número de compras
    top_clientes = ventas.values('cliente__nombres', 'cliente__apellidos').annotate(
        count=Count('id'),
        total=Sum('precio')
    ).order_by('-count')[:10]
    
    clientes_labels = [f"{c['cliente__nombres']} {c['cliente__apellidos']}" for c in top_clientes]
    clientes_data = [c['count'] for c in top_clientes]
    clientes_ingresos = [float(c['total'] or 0) for c in top_clientes]
    
    # Gráfica 4: Ventas por material
    ventas_por_material = ventas.values('material__nombre').annotate(
        count=Count('id'),
        total=Sum('precio')
    ).order_by('-count')[:10]
    
    material_labels = [m['material__nombre'] or 'Sin material' for m in ventas_por_material]
    material_data = [m['count'] for m in ventas_por_material]
    material_ingresos = [float(m['total'] or 0) for m in ventas_por_material]
    
    # Gráfica 5: Ingresos por semana (últimas 4 semanas)
    ingresos_semana = {}
    for i in range(4, -1, -1):
        fecha_inicio = now().date() - timedelta(weeks=i+1)
        fecha_fin = now().date() - timedelta(weeks=i)
        semana_label = f"Semana de {fecha_inicio.strftime('%d/%m')}"
        ingresos = ventas.filter(
            fecha__date__gte=fecha_inicio,
            fecha__date__lt=fecha_fin
        ).aggregate(total=Sum('precio'))['total'] or 0
        ingresos_semana[semana_label] = float(ingresos)
    
    # Gráfica 6: Ingresos por mes (últimos 6 meses)
    ingresos_mes = {}
    for i in range(6, -1, -1):
        fecha = now() - timedelta(days=30*i)
        mes_label = fecha.strftime('%b %Y')
        ingresos = ventas.filter(
            fecha__year=fecha.year,
            fecha__month=fecha.month
        ).aggregate(total=Sum('precio'))['total'] or 0
        ingresos_mes[mes_label] = float(ingresos)
    
    data = {
        'ventas_por_estado': {
            'labels': list(ventas_por_estado.keys()),
            'data': list(ventas_por_estado.values()),
        },
        'ingresos_por_estado': {
            'labels': list(ingresos_por_estado.keys()),
            'data': list(ingresos_por_estado.values()),
        },
        'top_clientes_compras': {
            'labels': clientes_labels,
            'data': clientes_data,
            'ingresos': clientes_ingresos,
        },
        'ventas_por_material': {
            'labels': material_labels,
            'data': material_data,
            'ingresos': material_ingresos,
        },
        'ingresos_por_semana': {
            'labels': list(ingresos_semana.keys()),
            'data': list(ingresos_semana.values()),
        },
        'ingresos_por_mes': {
            'labels': list(ingresos_mes.keys()),
            'data': list(ingresos_mes.values()),
        }
    }
    
    return JsonResponse(data)

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
