from django.db import OperationalError


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
