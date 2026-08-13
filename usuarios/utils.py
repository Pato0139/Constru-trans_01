import re


def limpiar_telefono(telefono):
    """Limpia el numero de telefono: quita espacios y caracteres especiales"""
    if not telefono:
        return telefono
    return re.sub(r"[^0-9]", "", telefono)


def limpiar_documento(documento):
    """Limpia el numero de documento: quita espacios y caracteres especiales"""
    if not documento:
        return documento
    return re.sub(r"[^0-9]", "", documento)


def get_account_switch_options(usuario):
    """Devuelve las cuentas/roles alternos disponibles para el usuario actual."""
    current_role = getattr(usuario, "rol", None)
    roles_map = {
        "admin": {
            "label": "Administrador",
            "panel": "usuarios:panel",
            "perfil": "usuarios:perfil_admin",
        },
        "cliente": {
            "label": "Cliente",
            "panel": "clientes:panel_cliente",
            "perfil": "clientes:perfil_cliente",
        },
        "conductor": {
            "label": "Conductor",
            "panel": "usuarios:panel_conductor",
            "perfil": "usuarios:perfil_conductor",
        },
    }

    return [
        {
            "role": role,
            "label": data["label"],
            "panel": data["panel"],
            "perfil": data["perfil"],
        }
        for role, data in roles_map.items()
        if role != current_role
    ]