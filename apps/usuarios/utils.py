import re


def limpiar_telefono(telefono):
    """Limpia el numero de telefono: quita espacios y caracteres especiales."""
    if not telefono:
        return telefono
    return re.sub(r"[^0-9]", "", str(telefono))


def normalizar_telefono(pais_codigo, telefono):
    """Normaliza un teléfono con el prefijo internacional y evita duplicar +57."""
    if telefono is None:
        return ""

    numero = str(telefono).strip()
    if not numero:
        return ""

    codigo = (str(pais_codigo) if pais_codigo is not None else "").strip()
    codigo_digits = re.sub(r"\D", "", codigo)
    numero_digits = re.sub(r"\D", "", numero)
    if not numero_digits:
        return ""

    if codigo_digits and numero_digits.startswith(codigo_digits):
        numero_digits = numero_digits[len(codigo_digits):]
        return f"+{codigo_digits}{numero_digits}"

    if codigo_digits:
        return f"+{codigo_digits}{numero_digits}"

    if numero.startswith("+") and numero_digits:
        return f"+{numero_digits}"

    return numero_digits


def contiene_solo_numeros(valor):
    """Indica si un valor numérico no contiene letras ni símbolos extraños.

    Admite dígitos y los separadores habituales de teléfono (espacios, +, -, paréntesis).
    Devuelve True también para valores vacíos o None.
    """
    if valor is None:
        return True
    return re.fullmatch(r"[0-9\s+()-]*", str(valor).strip()) is not None


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
