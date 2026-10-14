from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table


def render_factura_pdf(factura):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=factura.numero)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"<b>Factura {factura.numero}</b>", styles["Title"]),
        Paragraph(
            f"Fecha de emisión: {factura.fecha_emision:%Y-%m-%d}",
            styles["Normal"],
        ),
        Paragraph(
            f"Pedido: {factura.pedido.codigo_pedido}", styles["Normal"]
        ),
        Spacer(1, 0.5 * cm),
    ]
    tabla = [["Descripción", "Cantidad", "Precio unitario", "Subtotal"]]
    for d in factura.pedido.detalles.all():
        tabla.append(
            [
                d.material.nombre,
                str(d.cantidad),
                f"${d.precio_unitario}",
                f"${d.subtotal}",
            ]
        )
    tabla.append(["", "", "Total:", f"${factura.total}"])
    story.append(Table(tabla, colWidths=[8 * cm, 3 * cm, 3 * cm, 3 * cm]))
    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            f"<b>Saldo pendiente:</b> ${factura.saldo_pendiente}",
            styles["Normal"],
        )
    )
    doc.build(story)
    return buf.getvalue()
