from decimal import Decimal

CIUDADES_DESPACHO = [
    "Duitama",
    "Sogamoso",
    "Paipa",
    "Nobsa",
    "Tibasosa",
]

CIUDAD_ENVIO_GRATIS = "Duitama"
TARIFA_ENVIO_EXTERNA = Decimal("15000.00")
MONTO_MINIMO_PEDIDO = Decimal("50000.00")


def ciudad_valida(ciudad: str) -> bool:
    return ciudad.strip() in CIUDADES_DESPACHO


def calcular_tarifa_envio(ciudad_o_direccion: str) -> Decimal:
    if not ciudad_o_direccion:
        return Decimal("0.00")

    texto = str(ciudad_o_direccion).strip()
    if not texto:
        return Decimal("0.00")

    ciudad, _ = separar_direccion_destino(texto)
    ciudad_norm = ciudad.strip().lower()
    if not ciudad_norm:
        return Decimal("0.00")

    ciudades_norm = {c.lower() for c in CIUDADES_DESPACHO}
    if ciudad_norm not in ciudades_norm:
        return Decimal("0.00")

    if ciudad_norm == CIUDAD_ENVIO_GRATIS.lower():
        return Decimal("0.00")

    return TARIFA_ENVIO_EXTERNA


def construir_direccion_destino(*partes) -> str:
    valores = [str(parte).strip() for parte in partes if parte not in (None, "")]
    return " ".join(valores).strip()


def separar_direccion_destino(direccion: str):
    if not direccion:
        return "", ""

    texto = direccion.strip()
    if not texto:
        return "", ""

    if "," in texto:
        ciudad, detalle = texto.split(",", 1)
        ciudad = ciudad.strip()
        detalle = detalle.strip()
        if ciudad:
            return ciudad, detalle

    partes = texto.split()
    if not partes:
        return "", ""

    ciudad = partes[0].rstrip(",")
    detalle = " ".join(partes[1:]).strip()
    if ciudad in CIUDADES_DESPACHO:
        return ciudad, detalle

    if len(partes) == 1:
        return ciudad, ""

    return ciudad, detalle
