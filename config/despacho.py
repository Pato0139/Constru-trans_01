CIUDADES_DESPACHO = [
    'Bogotá',
    'Medellín',
    'Cali',
    'Barranquilla',
    'Cartagena',
]


def ciudad_valida(ciudad: str) -> bool:
    return ciudad.strip() in CIUDADES_DESPACHO


def construir_direccion_destino(*partes) -> str:
    valores = [str(parte).strip() for parte in partes if parte not in (None, '')]
    return ' '.join(valores).strip()


def separar_direccion_destino(direccion: str):
    if not direccion:
        return '', ''

    texto = direccion.strip()
    if not texto:
        return '', ''

    if ',' in texto:
        ciudad, detalle = texto.split(',', 1)
        ciudad = ciudad.strip()
        detalle = detalle.strip()
        if ciudad:
            return ciudad, detalle

    partes = texto.split()
    if not partes:
        return '', ''

    ciudad = partes[0].rstrip(',')
    detalle = ' '.join(partes[1:]).strip()
    if ciudad in CIUDADES_DESPACHO:
        return ciudad, detalle

    if len(partes) == 1:
        return ciudad, ''

    return ciudad, detalle
