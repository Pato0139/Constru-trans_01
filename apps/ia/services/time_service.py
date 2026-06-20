from datetime import datetime
from zoneinfo import ZoneInfo


ALIASES = {
    "argentina": "America/Argentina/Buenos_Aires",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "bogota": "America/Bogota",
    "bogotá": "America/Bogota",
    "colombia": "America/Bogota",
    "mexico": "America/Mexico_City",
    "méxico": "America/Mexico_City",
    "españa": "Europe/Madrid",
    "madrid": "Europe/Madrid",
    "chile": "America/Santiago",
    "peru": "America/Lima",
    "perú": "America/Lima",
}


US_ZONES = {
    "Nueva York (ET)": "America/New_York",
    "Chicago (CT)": "America/Chicago",
    "Denver (MT)": "America/Denver",
    "Los Ángeles (PT)": "America/Los_Angeles",
}


def es_de_dia(hour: int) -> bool:
    return 6 <= hour < 18


def periodo(hour: int) -> str:
    return "de día" if es_de_dia(hour) else "de noche"


def hora_lugar(nombre: str, tz_name: str) -> str:
    now = datetime.now(ZoneInfo(tz_name))
    return (
        f"En {nombre} son las {now.strftime('%H:%M')}, "
        f"es {periodo(now.hour)} "
        f"y la fecha es {now.strftime('%d/%m/%Y')}."
    )


def responder_hora(texto: str) -> str | None:
    t = texto.lower()

    partes = []

    if "estados unidos" in t or "usa" in t or "eeuu" in t:
        partes.append("En Estados Unidos hay varias zonas horarias:<br>")
        for label, tz in US_ZONES.items():
            now = datetime.now(ZoneInfo(tz))
            partes.append(
                f"- {label}: {now.strftime('%H:%M')} ({periodo(now.hour)}), {now.strftime('%d/%m/%Y')}<br>"
            )

    encontrados = []
    for alias, tz_name in ALIASES.items():
        if alias in t:
            encontrados.append((alias.title(), tz_name))

    # quita duplicados por timezone
    vistos = set()
    encontrados_unicos = []
    for nombre, tz in encontrados:
        if tz not in vistos:
            encontrados_unicos.append((nombre, tz))
            vistos.add(tz)

    for nombre, tz in encontrados_unicos:
        partes.append(hora_lugar(nombre, tz) + "<br>")

    if partes:
        return "".join(partes)

    return None

