CIUDADES_DESPACHO = [
    'Bogotá',
    'Medellín',
    'Cali',
    'Barranquilla',
    'Cartagena',
]


def ciudad_valida(ciudad: str) -> bool:
    return ciudad.strip() in CIUDADES_DESPACHO


def construir_direccion_destino(calle: str, carrera: str, numero: str, complemento: str = '') -> str:
    return f'{calle} {carrera} {numero} {complemento}'.strip()


def separar_direccion_destino(direccion: str):
    partes = direccion.strip().split()
    return (
        partes[0] if len(partes) > 0 else '',
        partes[1] if len(partes) > 1 else '',
        ' '.join(partes[2:]) if len(partes) > 2 else '',
    )
