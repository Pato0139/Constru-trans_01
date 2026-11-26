import xml.etree.ElementTree as ET
from decimal import Decimal
from xml.sax.saxutils import escape

import openpyxl
from django.contrib.staticfiles import finders
from django.db.models import F, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.timezone import now
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.catalogo.models import MaterialConstruccion as Material
from apps.logistica.models import Vehiculo
from apps.pedidos.models import Pedido
from apps.usuarios.models import Usuario
from apps.usuarios.views import admin_required
from config.utils import registrar_actividad

REPORT_FIELDS = {
    "clientes": [
        ("id", "ID"),
        ("nombre", "Nombre"),
        ("email", "Correo"),
        ("telefono", "Teléfono"),
        ("estado", "Estado"),
    ],
    "materiales": [
        ("id", "ID"),
        ("nombre", "Nombre"),
        ("tipo", "Tipo"),
        ("precio", "Precio"),
        ("stock", "Stock"),
    ],
    "ventas": [
        ("id", "ID"),
        ("cliente", "Cliente"),
        ("fecha", "Fecha"),
        ("total", "Total"),
        ("estado", "Estado"),
    ],
    "pedidos": [
        ("id", "ID"),
        ("cliente", "Cliente"),
        ("fecha", "Fecha"),
        ("materiales", "Materiales"),
        ("total", "Total"),
        ("estado", "Estado"),
    ],
}


def _report_data(tipo):
    fields = REPORT_FIELDS.get(tipo)
    if fields is None:
        raise Http404("Tipo de reporte no disponible.")

    if tipo == "clientes":
        records = [
            {
                "id": user.id,
                "nombre": f"{user.nombres} {user.apellidos}".strip(),
                "email": user.email,
                "telefono": user.telefono or "N/A",
                "estado": user.estado,
            }
            for user in Usuario.objects.filter(rol="cliente")
        ]
    elif tipo == "materiales":
        records = [
            {
                "id": material.id,
                "nombre": material.nombre,
                "tipo": material.tipo or "N/A",
                "precio": material.precio or Decimal("0"),
                "stock": material.stock,
            }
            for material in Material.objects.select_related("catalogo").all()
        ]
    else:
        pedidos = Pedido.objects.select_related("cliente__usuario").all()
        if tipo == "pedidos":
            pedidos = pedidos.prefetch_related("detalles__material")

        records = []
        for pedido in pedidos:
            cliente = pedido.cliente.usuario if pedido.cliente_id else None
            cliente_nombre = f"{cliente.nombres} {cliente.apellidos}".strip() if cliente else "N/A"
            fecha = pedido.fecha or pedido.fecha_solicitud
            record = {
                "id": pedido.id,
                "cliente": cliente_nombre,
                "fecha": fecha.strftime("%Y-%m-%d") if fecha else "N/A",
                "total": pedido.total or pedido.precio or Decimal("0"),
                "estado": pedido.estado,
            }
            if tipo == "pedidos":
                detalles = list(pedido.detalles.all())
                record["materiales"] = (
                    ", ".join(
                        f"{detalle.cantidad} x {detalle.material.nombre}" for detalle in detalles
                    )
                    or "Sin materiales"
                )
                record["detalles"] = detalles
            records.append(record)

    return fields, records


def _format_money(value):
    amount = Decimal(str(value or 0))
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@admin_required
def reportes_admin(request):
    pedidos = Pedido.objects.all()
    total = pedidos.count()
    pendientes = pedidos.filter(estado="pendiente").count()
    en_ruta = pedidos.filter(estado="en_ruta").count()
    entregadas = pedidos.filter(estado="entregado").count()
    otros = max(0, total - pendientes - en_ruta - entregadas)
    distribucion_ordenes = [
        {"label": "Pendientes", "value": pendientes, "color": "#f59e0b"},
        {"label": "En Ruta", "value": en_ruta, "color": "#3b82f6"},
        {"label": "Entregadas", "value": entregadas, "color": "#10b981"},
        {"label": "Otros", "value": otros, "color": "#94a3b8"},
    ]

    # Calcular porcentajes
    pct_pendientes = (pendientes * 100 / total) if total > 0 else 0
    pct_en_ruta = (en_ruta * 100 / total) if total > 0 else 0
    pct_entregadas = (entregadas * 100 / total) if total > 0 else 0

    # Materiales con stock crítico
    stock_critico = Material.objects.filter(
        stock_info__cantidad_actual__lt=F("stock_info__stock_minimo")
    ).select_related("stock_info")

    context = {
        # Resumen de Órdenes
        "total_ordenes": total,
        "pendientes": pendientes,
        "en_ruta": en_ruta,
        "entregadas": entregadas,
        "otros": otros,
        "distribucion_ordenes": distribucion_ordenes,
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
        "total_ingresos": pedidos.aggregate(total=Sum("total"))["total"] or 0,
        # Stock Crítico
        "stock_critico": stock_critico,
    }
    return render(request, "reportes/lista.html", context)


@admin_required
def exportar_reporte_pdf(request, tipo):
    fields, records = _report_data(tipo)
    generated_at = now()
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="reporte_{tipo}_{generated_at.strftime("%Y%m%d")}.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(letter),
        leftMargin=32,
        rightMargin=32,
        topMargin=30,
        bottomMargin=42,
    )
    elements = []
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="BrandTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=23,
            textColor=colors.HexColor("#172033"),
            alignment=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=colors.white,
        )
    )

    logo_path = finders.find("img/Logo1.jpeg")
    if not logo_path:
        raise FileNotFoundError("No se encontró el logo estático img/Logo1.jpeg.")

    brand = Paragraph(
        "<font size='8' color='#F59E0B'>CONSTRU TRANS</font><br/>"
        "<font size='7' color='#64748B'>GESTIÓN DE CONSTRUCCIÓN Y TRANSPORTE</font>",
        styles["Normal"],
    )
    brand_header = Table(
        [[Image(logo_path, width=76, height=42, kind="proportional"), brand]],
        colWidths=[96, doc.width - 96],
    )
    brand_header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 2, colors.HexColor("#F59E0B")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(brand_header)
    elements.append(Spacer(1, 18))
    elements.append(
        Paragraph(f"Reporte de {tipo.replace('_', ' ').capitalize()}", styles["BrandTitle"])
    )
    elements.append(Spacer(1, 5))
    elements.append(
        Paragraph(
            f"Generado: {generated_at.strftime('%Y-%m-%d %H:%M')} "
            f"&nbsp;&nbsp;|&nbsp;&nbsp; Registros: {len(records)}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 18))

    if records:
        data = [[Paragraph(escape(label), styles["ReportHeader"]) for _, label in fields]]
        for record in records:
            row = []
            for key, _ in fields:
                value = record[key]
                if key in {"precio", "total"}:
                    value = _format_money(value)
                row.append(Paragraph(escape(str(value)), styles["ReportCell"]))
            data.append(row)

        column_widths = {
            "clientes": [35, 145, 250, 120, 80],
            "materiales": [35, 180, 160, 110, 100],
            "ventas": [35, 165, 100, 115, 100],
            "pedidos": [35, 125, 85, 330, 90, 63],
        }[tipo]
        table = Table(data, colWidths=column_widths, repeatRows=1, splitByRow=1, splitInRow=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172033")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor("#F1F5F9"),
                        ],
                    ),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1E293B")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#F59E0B")),
                    ("GRID", (0, 1), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ]
            )
        )
        elements.append(table)
    else:
        elements.append(Paragraph("No hay datos disponibles para este reporte.", styles["Normal"]))

    def draw_footer(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.line(doc.leftMargin, 30, landscape(letter)[0] - doc.rightMargin, 30)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(doc.leftMargin, 18, "ConstruTrans · Reporte administrativo")
        canvas.drawRightString(
            landscape(letter)[0] - doc.rightMargin,
            18,
            f"Página {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)

    registrar_actividad(request, "otro", "reportes", None, f"Reporte de {tipo} exportado a PDF")

    return response


@admin_required
def exportar_reporte_excel(request, tipo):
    fields, records = _report_data(tipo)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Reporte {tipo.capitalize()}"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    center_aligned = Alignment(horizontal="center")

    headers = [label for _, label in fields]
    ws.append(headers)
    for record in records:
        ws.append([record[key] for key, _ in fields])

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_aligned
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            max_length = max(max_length, len(str(cell.value or "")))
        adjusted_width = max_length + 2
        ws.column_dimensions[column].width = adjusted_width

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="reporte_{tipo}_{now().strftime("%Y%m%d")}.xlsx"'
    )
    wb.save(response)

    registrar_actividad(request, "otro", "reportes", None, f"Reporte de {tipo} exportado a Excel")
    return response


@admin_required
def exportar_reporte_xml(request, tipo):
    fields, records = _report_data(tipo)
    root = ET.Element("reporte")
    root.set("tipo", tipo)
    root.set("fecha_generacion", now().strftime("%Y-%m-%d %H:%M:%S"))

    item_names = {
        "clientes": "cliente",
        "materiales": "material",
        "ventas": "venta",
        "pedidos": "pedido",
    }
    for record in records:
        item = ET.SubElement(root, item_names[tipo])
        for key, _ in fields:
            value = record[key]
            if key in {"precio", "total"}:
                value = str(value or 0)
            ET.SubElement(item, key).text = str(value)
        if tipo == "pedidos":
            details = ET.SubElement(item, "detalles")
            for detail in record["detalles"]:
                detail_node = ET.SubElement(details, "detalle")
                ET.SubElement(detail_node, "material").text = detail.material.nombre
                ET.SubElement(detail_node, "cantidad").text = str(detail.cantidad)

    # Convertir a string indentado
    from xml.dom import minidom

    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")

    response = HttpResponse(xmlstr, content_type="application/xml")
    response["Content-Disposition"] = (
        f'attachment; filename="reporte_{tipo}_{now().strftime("%Y%m%d")}.xml"'
    )

    registrar_actividad(request, "otro", "reportes", None, f"Reporte de {tipo} exportado a XML")
    return response
