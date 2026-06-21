import re


def limpiar_telefono(telefono):
    """Limpia el numero de telefono: quita espacios y caracteres especiales"""
    if not telefono:
        return telefono
    return re.sub(r"[^0-9]", "", telefono)
