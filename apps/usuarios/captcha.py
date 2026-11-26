"""
Verificación CAPTCHA visual generada y validada del lado del servidor.

Funciona tanto en modo nube como en modo local (offline), generando una imagen
PNG distorsionada con Pillow y guardando la respuesta únicamente en la sesión
del servidor (nunca en el HTML/JS del cliente).
"""

import base64
import io
import os
import random
import secrets
import time

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Alfabeto sin caracteres ambiguos (sin 0/O, 1/I/l)
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 5
_CHALLENGE_TTL_SECONDS = 300  # 5 minutos
_VERIFIED_TTL_SECONDS = 300   # 5 minutos
_MAX_ATTEMPTS = 5

SESSION_CHALLENGE_KEY = "login_captcha_challenge"
SESSION_VERIFIED_KEY = "login_captcha_verified"


def _load_font(size: int) -> ImageFont.ImageFont:
    """Carga una fuente TrueType disponible en Windows/Linux con fallback seguro."""
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
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


def _render_captcha_png_base64(code: str) -> str:
    """Genera una imagen PNG distorsionada con ruido, líneas y rotación por carácter."""
    width, height = 220, 74
    rng = random.SystemRandom()

    bg_color = (rng.randint(236, 248), rng.randint(238, 248), rng.randint(242, 252))
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Fondo con puntos de ruido sutiles
    for _ in range(180):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        tone = rng.randint(155, 220)
        draw.point((x, y), fill=(tone, tone, tone))

    # Líneas de interferencia detrás del texto
    for _ in range(5):
        x1, y1 = rng.randint(0, width // 3), rng.randint(0, height)
        x2, y2 = rng.randint(width // 2, width), rng.randint(0, height)
        line_color = (rng.randint(130, 185), rng.randint(140, 190), rng.randint(150, 205))
        draw.line((x1, y1, x2, y2), fill=line_color, width=rng.randint(1, 2))

    # Dibujar cada carácter con rotación, tamaño y color ligeramente distintos
    char_slot = (width - 28) // len(code)
    palette = [
        (23, 37, 84),   # azul marino
        (30, 41, 59),   # slate oscuro
        (124, 45, 18),  # ámbar oscuro
        (17, 24, 39),   # casi negro
        (30, 64, 175),  # azul fuerte
    ]

    for idx, ch in enumerate(code):
        font = _load_font(rng.randint(31, 36))
        char_img = Image.new("RGBA", (54, 64), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        color = rng.choice(palette)
        char_draw.text((10, 8), ch, font=font, fill=color)

        angle = rng.randint(-20, 20)
        rotated = char_img.rotate(angle, resample=Image.BICUBIC, expand=True)

        paste_x = 12 + idx * char_slot + rng.randint(-3, 4)
        paste_y = rng.randint(2, max(3, height - rotated.height - 2))
        img.paste(rotated, (paste_x, paste_y), rotated)

    # Arco/línea ligera al frente para dificultar OCR simple
    for _ in range(2):
        y_start = rng.randint(16, height - 16)
        y_end = rng.randint(16, height - 16)
        fg_line = (rng.randint(90, 150), rng.randint(100, 160), rng.randint(120, 175))
        draw.line((8, y_start, width - 8, y_end), fill=fg_line, width=1)

    img = img.filter(ImageFilter.SMOOTH)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def generar_reto_captcha(request) -> dict:
    """Crea un nuevo reto CAPTCHA en sesión y devuelve solo el ID y la imagen."""
    code = "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))
    challenge_id = secrets.token_urlsafe(16)
    now = time.time()

    request.session[SESSION_CHALLENGE_KEY] = {
        "id": challenge_id,
        "answer": code,
        "expires_at": now + _CHALLENGE_TTL_SECONDS,
        "attempts": 0,
    }
    request.session.pop(SESSION_VERIFIED_KEY, None)
    request.session.modified = True

    return {
        "challenge_id": challenge_id,
        "image": _render_captcha_png_base64(code),
    }


def verificar_reto_captcha(request, challenge_id: str, respuesta: str) -> tuple[bool, dict]:
    """Valida la respuesta del usuario contra el reto almacenado en sesión."""
    challenge = request.session.get(SESSION_CHALLENGE_KEY)
    now = time.time()

    if not challenge or not isinstance(challenge, dict):
        nuevo = generar_reto_captcha(request)
        return False, {
            "ok": False,
            "error": "El reto expiró. Resuelve el nuevo código.",
            "challenge": nuevo,
        }

    if now > float(challenge.get("expires_at", 0)):
        nuevo = generar_reto_captcha(request)
        return False, {
            "ok": False,
            "error": "El reto expiró. Resuelve el nuevo código.",
            "challenge": nuevo,
        }

    expected_id = str(challenge.get("id", ""))
    expected_answer = str(challenge.get("answer", ""))
    user_answer = (respuesta or "").strip().upper().replace(" ", "")

    if not challenge_id or not secrets.compare_digest(str(challenge_id), expected_id):
        nuevo = generar_reto_captcha(request)
        return False, {
            "ok": False,
            "error": "Reto inválido. Intenta con el nuevo código.",
            "challenge": nuevo,
        }

    if user_answer and secrets.compare_digest(user_answer, expected_answer):
        token = secrets.token_urlsafe(24)
        request.session.pop(SESSION_CHALLENGE_KEY, None)
        request.session[SESSION_VERIFIED_KEY] = {
            "token": token,
            "expires_at": now + _VERIFIED_TTL_SECONDS,
        }
        request.session.modified = True
        return True, {"ok": True, "token": token}

    attempts = int(challenge.get("attempts", 0)) + 1
    nuevo = generar_reto_captcha(request)
    if attempts >= _MAX_ATTEMPTS:
        msg = "Demasiados intentos fallidos. Se generó un nuevo código."
    else:
        msg = "Código incorrecto. Intenta con el nuevo código."
    return False, {"ok": False, "error": msg, "challenge": nuevo}


def validar_token_captcha(request, token: str, consumir: bool = True) -> bool:
    """Verifica del lado del servidor que el login tenga un CAPTCHA resuelto y vigente."""
    verified = request.session.get(SESSION_VERIFIED_KEY)
    if not verified or not isinstance(verified, dict):
        return False

    now = time.time()
    expected_token = str(verified.get("token", ""))
    expires_at = float(verified.get("expires_at", 0))

    if consumir:
        request.session.pop(SESSION_VERIFIED_KEY, None)
        request.session.modified = True

    if not token or not expected_token or now > expires_at:
        return False

    return secrets.compare_digest(str(token), expected_token)
