"""Recolector de preguntas públicas para el autoentrenamiento de la IA."""

import html
import logging
import random
import time

import requests

logger = logging.getLogger(__name__)
TIMEOUT = 15
UA = {"User-Agent": "ConstruTransIA/1.0 (autoentrenamiento local)"}
SITES_STACK = ["es.stackoverflow", "es.superuser", "es.askubuntu"]
CATEGORIAS_DOMINIO = [
    "Categoría:Materiales de construcción",
    "Categoría:Maquinaria de construcción",
    "Categoría:Ingeniería civil",
    "Categoría:Transporte",
    "Categoría:Logística",
    "Categoría:Camiones",
    "Categoría:Cemento",
    "Categoría:Hormigón",
    "Categoría:Construcción",
    "Categoría:Transporte por carretera",
]


def _limpiar(texto: str) -> str:
    return " ".join(html.unescape(texto or "").split()).strip()


def recolectar_opentdb(cantidad: int) -> list:
    try:
        response = requests.get(
            "https://opentdb.com/api.php",
            params={"amount": min(cantidad, 50), "type": "multiple", "lang": "es"},
            headers=UA,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return [
            {
                "pregunta": _limpiar(item.get("question", "")),
                "fuente": "opentdb",
                "metadata": {
                    "licencia": "CC BY-SA 4.0 (Open Trivia DB)",
                    "categoria": _limpiar(item.get("category", "")),
                    "respuesta_correcta": _limpiar(item.get("correct_answer", "")),
                    "dificultad": item.get("difficulty", ""),
                },
            }
            for item in response.json().get("results", [])
            if _limpiar(item.get("question", ""))
        ]
    except Exception as exc:
        logger.warning("OpenTDB falló: %s", exc)
        return []


def recolectar_stackexchange(cantidad: int) -> list:
    sitio = random.choice(SITES_STACK)
    try:
        response = requests.get(
            "https://api.stackexchange.com/2.3/questions",
            params={"order": "desc", "sort": "activity", "site": sitio, "pagesize": min(cantidad, 30), "filter": "!nNPvSNP4Rl*"},
            headers=UA,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        salida = []
        for item in response.json().get("items", []):
            titulo = _limpiar(item.get("title", ""))
            if titulo and not titulo.endswith("?"):
                titulo = f"¿{titulo}?"
            if titulo:
                salida.append({"pregunta": titulo, "fuente": "stackexchange", "metadata": {"licencia": "CC BY-SA (Stack Exchange)", "sitio": sitio, "tags": ", ".join(item.get("tags", [])[:5]), "link": item.get("link", "")}})
        return salida
    except Exception as exc:
        logger.warning("Stack Exchange falló: %s", exc)
        return []


def recolectar_wikipedia(cantidad: int) -> list:
    salida = []
    for _ in range(cantidad):
        try:
            time.sleep(2.5)
            response = requests.get("https://es.wikipedia.org/api/rest_v1/page/random/summary", headers=UA, timeout=TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            data = response.json()
            titulo, extracto = data.get("title", ""), (data.get("extract") or "").strip()
            if not titulo or len(extracto) < 120 or data.get("type") == "disambiguation":
                continue
            salida.append({"pregunta": f"¿Qué es {titulo}?", "fuente": "wikipedia", "metadata": {"licencia": "CC BY-SA (Wikipedia)", "link": data.get("content_urls", {}).get("desktop", {}).get("page", ""), "texto_referencia": extracto[:1200]}})
        except Exception as exc:
            logger.warning("Wikipedia falló: %s", exc)
    return salida


def recolectar_wikipedia_dominio(cantidad: int) -> list:
    salida = []
    por_categoria = max(1, cantidad // len(CATEGORIAS_DOMINIO) + 1)
    for categoria in CATEGORIAS_DOMINIO:
        if len(salida) >= cantidad:
            break
        try:
            time.sleep(2.0)
            response = requests.get("https://es.wikipedia.org/w/api.php", params={"action": "query", "generator": "categorymembers", "gcmtitle": categoria, "gcmlimit": min(por_categoria, 25), "gcmnamespace": "0", "prop": "extracts", "exintro": "1", "explaintext": "1", "format": "json"}, headers=UA, timeout=TIMEOUT)
            response.raise_for_status()
            pages = (response.json().get("query", {}) or {}).get("pages", {})
            for page in pages.values():
                titulo, extracto = page.get("title", ""), (page.get("extract") or "").strip()
                if not titulo or len(extracto) < 120 or ":" in titulo:
                    continue
                salida.append({"pregunta": f"¿Qué es {titulo}?", "fuente": "wikipedia_dominio", "metadata": {"licencia": "CC BY-SA (Wikipedia)", "categoria": categoria.replace("Categoría:", ""), "texto_referencia": extracto[:1500]}})
                if len(salida) >= cantidad:
                    break
        except Exception as exc:
            logger.warning("Wikipedia dominio (%s) falló: %s", categoria, exc)
    return salida


def recolectar(total: int, fuentes: list | None = None) -> list:
    fuentes = fuentes or ["opentdb", "stackexchange", "wikipedia", "wikipedia_dominio"]
    por_fuente = max(1, total // len(fuentes) + (1 if total % len(fuentes) else 0))
    recolectores = {"opentdb": recolectar_opentdb, "stackexchange": recolectar_stackexchange, "wikipedia": recolectar_wikipedia, "wikipedia_dominio": recolectar_wikipedia_dominio}
    preguntas = []
    for fuente in fuentes:
        recolector = recolectores.get(fuente)
        if recolector:
            preguntas.extend(recolector(por_fuente))
    random.shuffle(preguntas)
    return preguntas[:total]
