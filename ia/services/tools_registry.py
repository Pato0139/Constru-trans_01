"""Herramientas opcionales que el LLM puede ejecutar contra datos reales."""

import json
import logging
import os

logger = logging.getLogger(__name__)
TOOLS_ENABLED = os.getenv("TOOLS_ENABLED", "False").lower() == "true"
MAX_TOOL_ROUNDS = int(os.getenv("TOOLS_MAX_ROUNDS", "2"))


def _tools_definiciones():
    return [
        {"type": "function", "function": {"name": "consultar_estado_pedido", "description": "Consulta un pedido por su código.", "parameters": {"type": "object", "properties": {"codigo": {"type": "integer"}}, "required": ["codigo"]}}},
        {"type": "function", "function": {"name": "consultar_materiales", "description": "Lista materiales activos, opcionalmente filtrados por nombre.", "parameters": {"type": "object", "properties": {"busqueda": {"type": "string"}}}}},
        {"type": "function", "function": {"name": "consultar_stock_bajo", "description": "Lista materiales por debajo de su stock mínimo.", "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {"name": "contar_pedidos_por_estado", "description": "Cuenta pedidos por estado técnico.", "parameters": {"type": "object", "properties": {"estado": {"type": "string"}}, "required": ["estado"]}}},
        {"type": "function", "function": {"name": "calcular", "description": "Evalúa una expresión matemática segura.", "parameters": {"type": "object", "properties": {"expresion": {"type": "string"}}, "required": ["expresion"]}}},
    ]


def _estado_pedido(codigo):
    from pedidos.models import Pedido

    pedido = Pedido.objects.filter(codigo_pedido=codigo).first()
    if not pedido:
        return {"encontrado": False}
    return {"encontrado": True, "estado": pedido.estado, "cliente": str(pedido.cliente) if pedido.cliente else None, "total": str(pedido.total)}


def _materiales(busqueda=None):
    from catalogo.models import MaterialConstruccion

    queryset = MaterialConstruccion.objects.filter(activo=True)
    if busqueda:
        queryset = queryset.filter(nombre__icontains=busqueda)
    return {"total": queryset.count(), "materiales": [{"nombre": material.nombre, "precio": str(material.precio_referencia)} for material in queryset[:15]]}


def _stock_bajo():
    from django.db.models import F
    from catalogo.models import Stock

    queryset = Stock.objects.filter(cantidad_actual__lt=F("stock_minimo")).select_related("material")[:15]
    return {"total": len(queryset), "materiales": [{"material": item.material.nombre, "stock_actual": item.cantidad_actual, "stock_minimo": item.stock_minimo} for item in queryset]}


def _pedidos_estado(estado):
    from pedidos.models import Pedido

    validos = [choice[0] for choice in Pedido.ESTADOS]
    if estado not in validos:
        return {"error": f"Estado inválido. Válidos: {validos}"}
    return {"estado": estado, "cantidad": Pedido.objects.filter(estado=estado).count()}


def _calcular(expresion):
    from .math_service import evaluar_expresion_matematica

    return {"expresion": expresion, "resultado": evaluar_expresion_matematica(expresion)}


_EJECUTORES = {"consultar_estado_pedido": _estado_pedido, "consultar_materiales": _materiales, "consultar_stock_bajo": _stock_bajo, "contar_pedidos_por_estado": _pedidos_estado, "calcular": _calcular}


def ejecutar_tool(nombre, argumentos_json):
    try:
        argumentos = json.loads(argumentos_json or "{}")
        ejecutor = _EJECUTORES.get(nombre)
        if ejecutor is None:
            return json.dumps({"error": f"Tool desconocida: {nombre}"})
        return json.dumps(ejecutor(**argumentos), ensure_ascii=False, default=str)
    except json.JSONDecodeError:
        return json.dumps({"error": "Argumentos JSON inválidos"})
    except Exception as exc:
        logger.exception("Falló la tool %s", nombre)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def hay_tools():
    return TOOLS_ENABLED