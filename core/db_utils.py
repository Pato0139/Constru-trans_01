from django.db import OperationalError

def save_offline_first(instance, remote_db='remota', local_db='default'):
    """
    Intenta guardar una instancia en la base de datos remota.
    Si falla por problemas de conexión, la guarda localmente marcándola como no sincronizada.
    """
    try:
        # Intentamos guardar en la nube
        instance.save(using=remote_db)
        # Si tiene éxito, nos aseguramos que localmente esté marcada como sincronizada (si existe)
        instance.sincronizado = True
        instance.save(using=local_db)
        return True, "Sincronizado con la nube"
    except OperationalError:
        # Si falla la red, guardamos localmente con la bandera en False
        instance.sincronizado = False
        instance.save(using=local_db)
        return False, "Guardado localmente (Sin conexión)"
    except Exception as e:
        # Otros errores
        return False, f"Error: {str(e)}"
