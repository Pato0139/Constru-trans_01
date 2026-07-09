from django.conf import settings
from django.core.cache import cache

from usuarios.models import Notificacion
from core.db_preference import PREF_AUTO, debe_usar_bd_remota
from core.utils import conexion_remota_disponible


def notificaciones_context(request):
    if request.user.is_authenticated:
        cache_key = f"notif_user_{request.user.id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data

        try:
            if hasattr(request.user, "usuario"):
                usuario = request.user.usuario
                unread_ids = list(
                    Notificacion.objects.filter(usuario=usuario, leida=False).values_list(
                        "id", flat=True
                    )[:10]
                )
                unread_count = len(unread_ids)

                recientes_ids = list(
                    Notificacion.objects.filter(usuario=usuario)
                    .order_by("-fecha")
                    .values_list("id", flat=True)[:5]
                )

                if recientes_ids:
                    recientes = list(
                        Notificacion.objects.filter(id__in=recientes_ids).only(
                            "id", "titulo", "mensaje", "fecha", "leida", "tipo", "link"
                        )
                    )
                else:
                    recientes = []

                data = {
                    "notif_recent": recientes,
                    "notif_unread_count": unread_count,
                }
                cache.set(cache_key, data, 300)
                return data
        except Exception:
            pass

    return {
        "notif_recent": [],
        "notif_unread_count": 0,
    }


def modo_context(request):
    """Estado de BD local/remota y preferencia de sesión para la UI."""
    from django.core.cache import cache
    
    remota_configurada = "remota" in settings.DATABASES
    
    # Get remota_disponible from cache to avoid repeated expensive calls
    cache_key = "core:conexion_remota_disponible"
    remota_disponible = cache.get(cache_key)
    if remota_disponible is None and remota_configurada:
        remota_disponible = conexion_remota_disponible()
    elif not remota_configurada:
        remota_disponible = False
    
    try:
        from core.db_preference import debe_usar_bd_remota
        usando_remota = debe_usar_bd_remota() if remota_disponible else False
    except (ImportError, Exception):
        usando_remota = False
    
    preferencia = request.session.get("bd_preferida", "auto")

    if usando_remota:
        bd_etiqueta = "Remoto (Neon)"
        bd_icono = "bi-cloud-check-fill"
        bd_siguiente = "local"
    else:
        bd_etiqueta = "Local (SQLite)"
        bd_icono = "bi-hdd-network-fill"
        bd_siguiente = "remota"

    modo_local = not usando_remota
    modo_invitado = modo_local and (
        not request.user.is_authenticated or not hasattr(request.user, "usuario")
    )

    return {
        "modo_local": modo_local,
        "modo_invitado": modo_invitado,
        "bd_preferida": preferencia,
        "bd_usando_remota": usando_remota,
        "bd_remota_configurada": remota_configurada,
        "bd_remota_disponible": remota_disponible,
        "bd_etiqueta": bd_etiqueta,
        "bd_icono": bd_icono,
        "bd_siguiente_modo": bd_siguiente,
        "bd_puede_cambiar_a_remoto": remota_configurada,
    }
