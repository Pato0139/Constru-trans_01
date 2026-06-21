"""
Ciudades autorizadas para despacho (Boyacá y zona de influencia).
Opción B del informe: varias ciudades concretas con validación en formularios.
"""

CIUDADES_DESPACHO = [
    "Tunja",
    "Duitama",
    "Paipa",
    "Sogamoso",
    "Chiquinquirá",
    "Villa de Leyva",
    "Samacá",
    "Nobsa",
]

BODEGA_ORIGEN = "Bodega Central - Tunja"


def ciudad_valida(ciudad: str) -> bool:
    if not ciudad:
        return False
    return ciudad.strip() in CIUDADES_DESPACHO


def construir_direccion_destino(ciudad: str, detalle: str) -> str:
    ciudad = (ciudad or "").strip()
    detalle = (detalle or "").strip()
    if not ciudad:
        return detalle
    if not detalle:
        return ciudad
    return f"{ciudad} — {detalle}"


def separar_direccion_destino(direccion_completa: str) -> tuple[str, str]:
    if not direccion_completa:
        return "", ""
    texto = direccion_completa.strip()
    for ciudad in CIUDADES_DESPACHO:
        prefijos = (f"{ciudad} — ", f"{ciudad} - ", f"{ciudad}, ")
        for prefijo in prefijos:
            if texto.startswith(prefijo):
                return ciudad, texto[len(prefijo) :].strip()
        if texto == ciudad:
            return ciudad, ""
    return "", texto
