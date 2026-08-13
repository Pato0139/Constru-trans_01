import re


def limpiar_telefono(telefono):
    """Limpia el numero de telefono: quita espacios y caracteres especiales"""
    if not telefono:
        return telefono
    return re.sub(r"[^0-9]", "", telefono)


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


def get_account_switch_options(usuario):
    """Devuelve las cuentas/roles alternos disponibles para el usuario actual."""
    current_role = getattr(usuario, "rol", None)
    roles_map = {
        "admin": {"label": "Administrador", "panel": "usuarios:panel", "perfil": "usuarios:perfil_admin"},
        "cliente": {"label": "Cliente", "panel": "clientes:panel_cliente", "perfil": "clientes:perfil_cliente"},
        "conductor": {"label": "Conductor", "panel": "usuarios:panel_conductor", "perfil": "usuarios:perfil_conductor"},
    }

    return [
        {"role": role, "label": data["label"], "panel": data["panel"], "perfil": data["perfil"]}
        for role, data in roles_map.items()
        if role != current_role
    ]
