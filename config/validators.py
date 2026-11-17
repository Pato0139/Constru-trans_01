"""Validadores reutilizables del proyecto (fuente única de verdad).

Los modelos y formularios deben importar desde aquí en lugar de declarar
RegexValidator locales. Así las reglas son idénticas en todo el sistema.
"""

import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.utils.deconstruct import deconstructible

# ---------------------------------------------------------------------------
# Formatos
# ---------------------------------------------------------------------------
numeric_and_space_validator = RegexValidator(
    r"^[0-9 ]+$",
    message="Este campo solo puede contener números y espacios.",
    code="formato_numerico",
)

# Colombia: celular (10 dígitos inicia en 3), fijo nacional (10 dígitos inicia en 601-608),
# fijo local (7 dígitos) o indicativos antiguos. Admite +57, espacios y guiones como separadores.
telefono_validator = RegexValidator(
    r"^(\+?57[ -]?)?(3\d{2}[ -]?\d{3}[ -]?\d{4}|60[1-8][ -]?\d{3}[ -]?\d{4}|[1-8][ -]?\d{3}[ -]?\d{4}|\d{7,10})$",
    message="Ingresa un teléfono válido (celular de 10 dígitos o fijo nacional).",
    code="telefono_invalido",
)

documento_validator = RegexValidator(
    r"^[0-9A-Za-z]{4,20}$",
    message="El documento debe tener entre 4 y 20 caracteres alfanuméricos, sin espacios.",
    code="documento_invalido",
)

# NIT o documento de identificación fiscal: 4-15 dígitos, opcionalmente con dígito de verificación "-N".
nit_validator = RegexValidator(
    r"^\d{4,15}(-\d)?$",
    message="El NIT debe tener entre 4 y 15 dígitos y, opcionalmente, '-' y el dígito de verificación.",
    code="nit_invalido",
)

# Placas Colombia y códigos de flota (ABC123, ABC-123, ABC12D, CTV0336, EXTRA01).
placa_validator = RegexValidator(
    r"^(?:[A-Z]{3}[- ]?\d{3,4}|[A-Z]{3}[- ]?\d{2}[A-Z0-9]|[A-Z0-9]{5,8})$",
    message="La placa debe ser un identificador alfanumérico válido (ej. ABC123, ABC-123, CTV0336).",
    code="placa_invalida",
)


@deconstructible
class NoSoloEspaciosValidator:
    message = "Este campo no puede estar vacío ni contener solo espacios."
    code = "solo_espacios"

    def __call__(self, value):
        if isinstance(value, str) and value and not value.strip():
            raise ValidationError(self.message, code=self.code)

    def __eq__(self, other):
        return isinstance(other, NoSoloEspaciosValidator)


no_solo_espacios = NoSoloEspaciosValidator()


# Símbolos "básicos" que sí se aceptan en textos con cifras (direcciones,
# unidades de medida, materiales, marcadores internos [-] (:) del sistema).
# Todo lo demás (comillas, $, %, &, @, *, etc.) se bloquea.
SIMBOLOS_BASICOS = "-#/.,°º()[]:²³"

_LETRAS = r"[^\W\d_]"  # cualquier letra (incluye tildes y ñ), sin dígitos ni "_"


@deconstructible
class _TextoPlanoValidator:
    """Rechaza símbolos en campos de texto.

    - ``permitir_numeros=True`` (por defecto): admite letras (incluidas tildes/ñ),
      dígitos y espacios.
    - ``permitir_numeros=False``: solo letras y espacios (ej. nombres, ciudades).
    - ``permitir_saltos=True``: permite saltos de línea (campos ``TextArea`` largos).
    - ``simbolos``: cadena con los símbolos adicionales permitidos (ej. ``-#/.``).
    """

    def __init__(self, permitir_numeros=True, permitir_saltos=False, simbolos=""):
        self.permitir_numeros = permitir_numeros
        self.permitir_saltos = permitir_saltos
        self.simbolos = simbolos
        partes = [_LETRAS]
        if permitir_numeros:
            partes.append(r"\d")
        partes.append(r"\s" if permitir_saltos else " ")
        partes.extend(re.escape(c) for c in simbolos)
        self._patron = re.compile(rf"^(?:{'|'.join(partes)})*$")

    @property
    def code(self):
        return "simbolos_no_permitidos"

    @property
    def message(self):
        if self.permitir_numeros:
            return "Este campo solo admite letras, números, espacios y símbolos básicos (sin otros símbolos)."
        return "Este campo solo admite letras y espacios (sin números ni símbolos)."

    def __call__(self, value):
        if value in (None, ""):
            return
        texto = str(value)
        if not texto.strip() or not self._patron.match(texto):
            raise ValidationError(self.message, code=self.code)

    def __eq__(self, other):
        return (
            isinstance(other, _TextoPlanoValidator)
            and self.permitir_numeros == other.permitir_numeros
            and self.permitir_saltos == other.permitir_saltos
            and self.simbolos == other.simbolos
        )


# Solo letras y espacios: nombres propios, apellidos, ciudades, roles, títulos.
solo_letras = _TextoPlanoValidator(permitir_numeros=False)

# Letras, números, espacios y símbolos básicos (direcciones, marcas tipo
# "Mercedes-Benz", modelos, empresas, descripciones).
texto_sin_simbolos = _TextoPlanoValidator(
    permitir_numeros=True, simbolos=SIMBOLOS_BASICOS
)

# Igual al anterior pero admitiendo saltos de línea (campos TextArea).
texto_multilinea = _TextoPlanoValidator(
    permitir_numeros=True, permitir_saltos=True, simbolos=SIMBOLOS_BASICOS
)

# ---------------------------------------------------------------------------
# Rangos numéricos
# ---------------------------------------------------------------------------
CANTIDAD_MAXIMA = 100_000

no_negativo = MinValueValidator(Decimal("0"), message="El valor no puede ser negativo.")
monto_positivo = MinValueValidator(Decimal("0.01"), message="El monto debe ser mayor que cero.")
porcentaje_validators = [
    MinValueValidator(Decimal("0"), message="El porcentaje no puede ser negativo."),
    MaxValueValidator(Decimal("100"), message="El porcentaje no puede superar 100."),
]
cantidad_validators = [
    MinValueValidator(1, message="La cantidad mínima es 1."),
    MaxValueValidator(CANTIDAD_MAXIMA, message=f"La cantidad no puede superar {CANTIDAD_MAXIMA}."),
]

# ---------------------------------------------------------------------------
# Archivos (extensión + firma real + peso)
# ---------------------------------------------------------------------------
_FIRMAS = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "webp": (b"RIFF",),
    "pdf": (b"%PDF-",),
}


@deconstructible
class ArchivoValidator:
    """Valida extensión, peso y que los bytes reales correspondan al tipo."""

    def __init__(self, extensiones=("png", "jpg", "jpeg"), max_mb=5):
        self.extensiones = tuple(e.lower() for e in extensiones)
        self.max_mb = max_mb

    def __call__(self, archivo):
        if not archivo:
            return
        nombre = (getattr(archivo, "name", "") or "").lower()
        ext = nombre.rsplit(".", 1)[-1] if "." in nombre else ""
        if ext not in self.extensiones:
            raise ValidationError(
                "Tipo de archivo no permitido. Extensiones válidas: %(ext)s.",
                code="extension_invalida",
                params={"ext": ", ".join(self.extensiones)},
            )
        if getattr(archivo, "size", 0) > self.max_mb * 1024 * 1024:
            raise ValidationError(
                "El archivo supera el límite de %(mb)s MB.",
                code="archivo_grande",
                params={"mb": self.max_mb},
            )
        if not self._firma_coincide(archivo, ext):
            raise ValidationError(
                "El contenido del archivo no coincide con su extensión.",
                code="mime_invalido",
            )

    @staticmethod
    def _firma_coincide(archivo, ext):
        firmas = _FIRMAS.get(ext)
        if not firmas:
            return True
        try:
            pos = archivo.tell()
        except Exception:
            pos = None
        try:
            archivo.seek(0)
            cabecera = archivo.read(12)
        except Exception:
            return False
        finally:
            if pos is not None:
                try:
                    archivo.seek(pos)
                except Exception:
                    pass
        if ext == "webp":
            return cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WEBP"
        return any(cabecera.startswith(f) for f in firmas)

    def __eq__(self, other):
        return (
            isinstance(other, ArchivoValidator)
            and self.extensiones == other.extensiones
            and self.max_mb == other.max_mb
        )


imagen_validator = ArchivoValidator(("png", "jpg", "jpeg"), max_mb=5)
