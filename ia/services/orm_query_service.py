import logging
import re

from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

ESTADO_PEDIDO = {
    "pendiente": "Pendiente",
    "autorizado_despacho": "Autorizado para despacho",
    "vehiculo_asignado": "Vehículo asignado",
    "en_ruta": "En ruta",
    "entregado": "Entregado",
    "cancelado": "Cancelado",
}


def _format_number(value):
    try:
        entero, _, decimal = f"{value:.2f}".partition(".")
        entero = f"{int(entero):,}".replace(",", ".")
        return f"{entero},{decimal}" if decimal != "00" else entero
    except (TypeError, ValueError):
        return str(value or 0)


def _extraer_codigo_pedido(mensaje):
    match = re.search(r"(?:pedido|orden)\s*(?:n[úu]mero|n[º°]|#)?\s*(\d+)", mensaje or "", re.IGNORECASE)
    if not match:
        match = re.search(r"\b(\d{1,6})\b", mensaje or "")
    return int(match.group(1)) if match else None


def consultar_pedido(codigo):
    from ordenes.models import Pedido

    pedido = Pedido.objects.filter(codigo_pedido=codigo).select_related("cliente", "usuario").prefetch_related("detalles__material").first()
    if not pedido:
        return None
    detalles = []
    for detalle in pedido.detalles.all()[:10]:
        try:
            detalles.append(
                f"- {detalle.material.nombre}: "
                f"{detalle.cantidad} x ${_format_number(detalle.precio_unitario)}"
            )
        except ObjectDoesNotExist:
            logger.warning("Detalle %s sin material para pedido %s", detalle.pk, codigo)
    partes = [
        f"Pedido #{pedido.codigo_pedido}",
        f"Estado: {ESTADO_PEDIDO.get(pedido.estado, pedido.estado)}",
        f"Cliente: {f'#{pedido.cliente_id}' if pedido.cliente_id else 'Sin cliente'}",
        f"Total: ${_format_number(pedido.total)}",
        "Materiales: " + ("; ".join(detalles) if detalles else "sin detalles registrados"),
    ]
    if pedido.fecha_entrega_programada:
        partes.append(f"Entrega programada: {pedido.fecha_entrega_programada.strftime('%d/%m/%Y %H:%M')}")
    if pedido.direccion_destino:
        partes.append(f"Destino: {pedido.direccion_destino}")
    return "\n".join(partes)


def consultar_materiales(mensaje):
    from usuarios.models import MaterialConstruccion

    query = re.sub(r"(cuales|cuáles|qué|que|materiales|tienes|hay|manejan|lista|catalogo|catálogo|precio)", "", mensaje or "", flags=re.IGNORECASE).strip()
    materiales = MaterialConstruccion.objects.filter(activo=True).select_related("unidad_medida", "marca")
    if 3 <= len(query) <= 60:
        filtrados = materiales.filter(nombre__icontains=query)
        if filtrados.exists():
            materiales = filtrados
    materiales = list(materiales[:15])
    if not materiales:
        return "No hay materiales registrados que coincidan con tu búsqueda."
    return "Materiales del catálogo:\n" + "\n".join(
        f"- {material.nombre} ({material.unidad_medida}): ${_format_number(material.precio_referencia)}"
        for material in materiales
    )


def consultar_pedidos_cliente(mensaje, usuario):
    from ordenes.models import Pedido

    consulta = Pedido.objects.all().order_by("-fecha_solicitud")
    if usuario and usuario.is_authenticated and getattr(usuario, "rol", None) not in {"admin", "empleado", "administrador"}:
        consulta = consulta.filter(usuario=usuario)
    mensaje_lower = (mensaje or "").lower()
    if "pendiente" in mensaje_lower:
        consulta = consulta.filter(estado="pendiente")
    elif "en ruta" in mensaje_lower or "en camino" in mensaje_lower:
        consulta = consulta.filter(estado="en_ruta")
    pedidos = list(consulta[:10])
    if not pedidos:
        return "No encontré pedidos que coincidan."
    return "Pedidos:\n" + "\n".join(
        f"- Pedido #{pedido.codigo_pedido}: {ESTADO_PEDIDO.get(pedido.estado, pedido.estado)} - ${_format_number(pedido.total)}"
        for pedido in pedidos
    )


def consultar_datos(mensaje, usuario=None):
    """Responde consultas verificables desde la BD antes de llamar al LLM."""
    try:
        mensaje_lower = (mensaje or "").lower()
        codigo = _extraer_codigo_pedido(mensaje)
        if re.search(r"pedido|orden", mensaje_lower) and codigo:
            respuesta = consultar_pedido(codigo)
            if respuesta:
                return respuesta
        if re.search(r"material|inventario|stock|cat[áa]logo|precio", mensaje_lower):
            return consultar_materiales(mensaje)
        if re.search(r"pedido|pendiente|mis pedidos", mensaje_lower):
            return consultar_pedidos_cliente(mensaje, usuario)
    except Exception:
        logger.exception("Error en la consulta ORM de IA")
    return None
