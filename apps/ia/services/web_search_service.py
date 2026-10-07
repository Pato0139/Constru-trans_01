"""Búsqueda web opcional para preguntas generales y de actualidad."""

import logging
import os
import re

logger = logging.getLogger(__name__)

WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED", "False").lower() in {"1", "true", "yes"}
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "4"))
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")

GENERAL_PATTERNS = [
    r"qui[eé]n (es|fue|era|gan[oó])",
    r"qu[eé] es\b",
    r"historia (de|del)",
    r"eventos? (importantes|significativos|históricos?)",
    r"qu[eé] ocurri[oó] en",
    r"qu[eé] pas[oó] en",
    r"durante (abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|enero|febrero|marzo) de \d{4}",
    r"en (abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|enero|febrero|marzo) de \d{4}",
    r"capital de",
    r"noticias?",
    r"actualidad",
    r"clima",
    r"tiempo en ",
    r"precio del d[oó]lar",
    r"tasa de cambio",
    r"presidente",
    r"selecci[oó]n",
    r"partido",
    r"resultado(s)? de",
    r"cu[aá]ndo (fue|naci[oó]|se fund[oó])",
    r"cu[aá]ntos habitantes",
    r"traduce|traducci[oó]n",
    r"receta|c[oó]mo se hace",
    r"significado de|sin[oó]nimo|ejemplo de",
]

SYSTEM_HINTS = [
    r"pedido", r"factura", r"inventario", r"stock", r"proveedor", r"cliente",
    r"veh[ií]culo", r"conductor", r"compra", r"pago", r"constru[- ]?trans",
    r"mi[s]? pedidos",
]


def _es_pregunta_general(mensaje):
    texto = (mensaje or "").lower()
    if any(re.search(patron, texto) for patron in SYSTEM_HINTS):
        return False
    return any(re.search(patron, texto) for patron in GENERAL_PATTERNS)


def buscar_web(query, k=None):
    if not WEB_SEARCH_ENABLED:
        return ""
    cantidad = k or WEB_SEARCH_MAX_RESULTS
    try:
        if BRAVE_API_KEY:
            return _buscar_brave(query, cantidad)
        return _buscar_ddg(query, cantidad)
    except Exception:
        logger.exception("Búsqueda web falló; se continúa sin contexto web")
        return ""


def buscar_web_si_aplica(mensaje):
    return buscar_web(mensaje) if _es_pregunta_general(mensaje) else ""


def _buscar_brave(query, cantidad):
    import requests

    respuesta = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": cantidad},
        headers={
            "X-Subscription-Token": BRAVE_API_KEY,
            "Accept": "application/json",
        },
        timeout=8,
    )
    respuesta.raise_for_status()
    resultados = respuesta.json().get("web", {}).get("results", [])
    return "\n".join(
        f"- {item.get('title', '')}: {item.get('description', '')} "
        f"(fuente: {item.get('url', '')})"
        for item in resultados
    )


def _buscar_ddg(query, cantidad):
    try:
        from ddgs import DDGS
    except ImportError:
        logger.warning("El paquete ddgs no está instalado; búsqueda web desactivada")
        return ""

    resultados = DDGS().text(query, max_results=cantidad)
    return "\n".join(
        f"- {item.get('title', '')}: {item.get('body', '')} "
        f"(fuente: {item.get('href', '')})"
        for item in resultados
    )
