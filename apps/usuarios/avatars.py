"""
Generador de fotos de perfil estilo Google (inicial + color único determinista).

Genera una imagen PNG 256x256 nítida con Pillow para cada usuario nuevo o existente
que no tenga foto de perfil cargada.
"""

import hashlib
import io
import logging
import os

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

GOOGLE_AVATAR_PALETTE = (
    "#1A73E8",  # Google Blue
    "#D93025",  # Google Red
    "#1E8E3E",  # Google Green
    "#E37400",  # Google Orange
    "#9334E6",  # Purple
    "#00897B",  # Teal
    "#C2185B",  # Pink
    "#3949AB",  # Indigo
    "#0097A7",  # Cyan
    "#5E35B1",  # Deep Purple
    "#039BE5",  # Light Blue
    "#689F38",  # Olive Green
)


def inicial_para_usuario(usuario) -> str:
    """Devuelve la letra inicial en mayúscula para el avatar del usuario."""
    for attr in ("nombres", "first_name", "username", "email"):
        val = (getattr(usuario, attr, "") or "").strip()
        if val:
            return val[0].upper()
    return "U"


def color_para_usuario(usuario) -> str:
    """Selecciona un color estilo Google determinista según la identidad del usuario."""
    seed = (
        (getattr(usuario, "email", "") or "").strip().lower()
        or (getattr(usuario, "username", "") or "").strip().lower()
        or str(getattr(usuario, "pk", "") or "usuario")
    )
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return GOOGLE_AVATAR_PALETTE[digest[0] % len(GOOGLE_AVATAR_PALETTE)]


def _cargar_fuente_avatar(size: int) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arialbd.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def generar_avatar_png_bytes(inicial: str, color_hex: str, size: int = 256) -> bytes:
    """Renderiza un PNG cuadrado 256x256 con fondo de color Google y letra centrada."""
    letra = (inicial or "U").strip()[:1].upper()
    hex_clean = color_hex.lstrip("#")
    r, g, b = tuple(int(hex_clean[i : i + 2], 16) for i in (0, 2, 4))

    img = Image.new("RGB", (size, size), (r, g, b))
    draw = ImageDraw.Draw(img)

    # Sutil iluminación superior para profundidad limpia tipo Material
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.ellipse(
        (-size * 0.15, -size * 0.35, size * 1.15, size * 0.72),
        fill=(255, 255, 255, 22),
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    font = _cargar_fuente_avatar(int(size * 0.48))
    bbox = draw.textbbox((0, 0), letra, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pos_x = (size - text_w) / 2 - bbox[0]
    pos_y = (size - text_h) / 2 - bbox[1]

    draw.text((pos_x, pos_y), letra, font=font, fill=(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _tiene_archivo_valido(usuario) -> bool:
    foto = getattr(usuario, "foto_perfil", None)
    if not foto or not getattr(foto, "name", ""):
        return False
    try:
        return foto.storage.exists(foto.name)
    except Exception:
        return False


def asegurar_avatar_usuario(usuario, *, using: str = "default", force: bool = False) -> bool:
    """
    Si el usuario no tiene foto de perfil (o el archivo no existe en disco),
    genera su avatar estilo Google y guarda la referencia en la BD indicada.
    """
    if not usuario or not getattr(usuario, "pk", None):
        return False
    if not force and _tiene_archivo_valido(usuario):
        return False

    inicial = inicial_para_usuario(usuario)
    color = color_para_usuario(usuario)
    png_bytes = generar_avatar_png_bytes(inicial, color)
    filename = f"avatar_{usuario.pk}_{inicial.lower()}.png"

    try:
        usuario.foto_perfil.save(filename, ContentFile(png_bytes), save=False)
        usuario.__class__._base_manager.using(using).filter(pk=usuario.pk).update(
            foto_perfil=usuario.foto_perfil.name
        )
        return True
    except Exception as exc:
        logger.warning(
            "No se pudo generar avatar automático para usuario %s: %s",
            getattr(usuario, "username", usuario.pk),
            exc,
        )
        return False
