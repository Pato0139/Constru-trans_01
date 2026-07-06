from django.db import OperationalError, connections


def should_use_select_for_update(alias="default"):
    """Devuelve True solo cuando la base de datos admite bloqueos de fila reales."""
    try:
        connection = connections[alias]
        return connection.features.supports_select_for_update
    except Exception:
        return False


def select_for_update_if_supported(queryset, alias="default"):
    """Aplica select_for_update solo en backends que lo soportan de forma real."""
    if should_use_select_for_update(alias):
        return queryset.select_for_update()
    return queryset


def save_offline_first(instance, remote_db="remota", local_db="default"):
    """
    Intenta guardar una instancia en la base de datos remota.
    Si falla por problemas de conexión, la guarda localmente marcándola como no sincronizada.
    """
    try:
        instance.save(using=remote_db)
        instance.sincronizado = True
        instance.save(using=local_db)
        return True, "Sincronizado con la nube"
    except OperationalError:
        instance.sincronizado = False
        instance.save(using=local_db)
        return False, "Guardado localmente (Sin conexión)"
    except Exception as e:
        return False, f"Error: {str(e)}"
