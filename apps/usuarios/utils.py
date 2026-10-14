import re


def limpiar_documento(documento):
    """Normaliza un documento: elimina espacios y caracteres no numéricos."""
    if not documento:
        return documento
    return re.sub(r"[^0-9]", "", str(documento))


def limpiar_telefono(telefono):
    """Limpia el numero de telefono: quita espacios y caracteres especiales"""
    if not telefono:
        return telefono
    return re.sub(r"[^0-9]", "", str(telefono))


def limpiar_documento(documento):
    """Normaliza un documento de identidad.

    - Si el documento contiene alguna letra, elimina caracteres no alfanuméricos
      y devuelve la cadena en mayúsculas (útil para pasaportes/NITs).
    - Si el documento es numérico, deja solo dígitos.
    - Si el valor es `None` o cadena vacía, lo devuelve tal cual.
    """
    if documento is None:
        return None

    doc = str(documento).strip()
    if not doc:
        return doc

    # Si contiene alguna letra, mantener letras y números y normalizar a mayúsculas
    if re.search(r"[A-Za-z]", doc):
        cleaned = re.sub(r"[^0-9A-Za-z]", "", doc)
        return cleaned.upper()

    # Si no tiene letras, devolver solo los dígitos
    digits = re.sub(r"[^0-9]", "", doc)
    return digits
