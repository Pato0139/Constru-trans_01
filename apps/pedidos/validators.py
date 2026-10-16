"""Validacion de servidor para archivos subidos.

El navegador puede saltarse el atributo ``accept`` y todo el JavaScript, y el
``content_type`` que viaja en la peticion lo controla el cliente. Por eso aqui el
tipo de archivo se comprueba leyendo los bytes reales (magic number) y no
confiando en lo que declara el navegador.
"""

from django.core.exceptions import ValidationError

EXTENSIONES_PERMITIDAS = (".png", ".jpg", ".jpeg")
TAMANO_MAXIMO_MB = 5
TAMANO_MAXIMO_BYTES = TAMANO_MAXIMO_MB * 1024 * 1024

# Firma real de cada formato que aceptamos
FIRMAS = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)


def tipo_real(archivo):
    """Devuelve el MIME real segun los bytes iniciales, o None si no es PNG/JPG."""
    try:
        posicion = archivo.tell()
    except Exception:
        posicion = None
    try:
        archivo.seek(0)
        cabecera = archivo.read(8)
    finally:
        if posicion is not None:
            try:
                archivo.seek(posicion)
            except Exception:
                pass
    for firma, mime in FIRMAS:
        if cabecera.startswith(firma):
            return mime
    return None


def validar_comprobante_imagen(archivo):
    """Valida extension, tamano y contenido real del comprobante."""
    if not archivo:
        return archivo

    nombre = (getattr(archivo, "name", "") or "").lower()
    if not nombre.endswith(EXTENSIONES_PERMITIDAS):
        raise ValidationError("Solo se permiten archivos PNG o JPG.")

    if getattr(archivo, "size", 0) > TAMANO_MAXIMO_BYTES:
        raise ValidationError(
            "El archivo supera el limite de %s MB." % TAMANO_MAXIMO_MB
        )

    if tipo_real(archivo) is None:
        raise ValidationError(
            "El archivo no es una imagen PNG o JPG valida: el contenido no "
            "coincide con la extension declarada."
        )

    return archivo
