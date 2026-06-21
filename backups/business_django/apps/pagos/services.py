from apps.usuarios.models import Notificacion


def crear_notificacion_pago(usuario, pago, tipo="info"):
    """
    Crea una notificación para el usuario sobre un pago
    """
    if pago.estado == "completado":
        titulo = "¡Pago completado!"
        mensaje = f"Tu pago de ${pago.monto} ha sido procesado exitosamente."
        tipo = "success"
    elif pago.estado == "pendiente":
        titulo = "Pago pendiente"
        mensaje = f"Tu pago de ${pago.monto} está pendiente de confirmación."
    elif pago.estado == "fallido":
        titulo = "Pago fallido"
        mensaje = f"Tu pago de ${pago.monto} no se pudo procesar. Por favor, intenta de nuevo."
        tipo = "danger"
    elif pago.estado == "reembolsado":
        titulo = "Reembolso realizado"
        mensaje = f"Se ha procesado un reembolso de ${pago.monto}."
        tipo = "warning"
    else:
        titulo = "Nuevo pago"
        mensaje = f"Se ha registrado un pago de ${pago.monto}."

    Notificacion.objects.create(
        usuario=usuario, titulo=titulo, mensaje=mensaje, tipo=tipo, link=f"/pagos/{pago.id_pago}/"
    )
