from django.utils import timezone


def registrar_estado_pago(payment, order, nuevo_estado, motivo_rechazo=None):
    payment.estado_pago = nuevo_estado
    if motivo_rechazo:
        payment.motivo_rechazo = motivo_rechazo
    if nuevo_estado == "pago aprobado":
        order.estado = "autorizado_despacho"
        payment.motivo_rechazo = ""
    elif nuevo_estado == "pago rechazado":
        order.estado = "pendiente"
    elif nuevo_estado == "contra_entrega":
        order.estado = "pendiente"
    elif nuevo_estado == "en_revision":
        order.estado = "pendiente"
    payment.fecha_actualizacion = timezone.now()
    return True
