from datetime import timedelta
from decimal import Decimal
import logging

from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.logistica.models import ConductorVehiculo, Entrega, Novedad, Vehiculo
from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.pedidos.utils import liberar_vehiculo_pedido, revertir_stock_pedido
from apps.usuarios.models import Conductor, Notificacion, Usuario
from config.db_utils import select_for_update_if_supported

logger = logging.getLogger(__name__)


def _resolver_db_alias(obj=None, using=None):
    if using:
        return using
    if obj is not None and getattr(obj, "_state", None) and obj._state.db:
        return obj._state.db
    return "default"


def _resolver_usuario_en_db(usuario, db_alias="default"):
    if usuario is None or not getattr(usuario, "pk", None):
        return None
    if getattr(usuario, "_state", None) and usuario._state.db == db_alias:
        return usuario
    encontrado = Usuario.objects.using(db_alias).filter(pk=usuario.pk).first()
    if encontrado:
        return encontrado
    if getattr(usuario, "username", None):
        return Usuario.objects.using(db_alias).filter(username=usuario.username).first()
    return None


def crear_notificacion_unica(usuario, titulo, mensaje, tipo="info", link=None, using="default"):
    """Crea una notificación para el destinatario garantizando idempotencia por (usuario, titulo)."""
    destinatario = _resolver_usuario_en_db(usuario, db_alias=using)
    if destinatario is None:
        return None

    existente = (
        Notificacion.objects.using(using)
        .filter(usuario=destinatario, titulo=titulo)
        .first()
    )
    if existente:
        return existente

    notif = Notificacion.objects.using(using).create(
        usuario=destinatario,
        titulo=titulo,
        mensaje=mensaje,
        tipo=tipo,
        link=link,
    )
    cache.delete(f"notif_user_{destinatario.pk}")
    return notif


def _obtener_administradores_activos(using="default"):
    return list(
        Usuario.objects.using(using)
        .filter(models_q_admin(), is_active=True)
        .exclude(estado__in=["inactivo", "suspendido"])
        .order_by("id")
    )


def models_q_admin():
    from django.db.models import Q

    return Q(rol="admin") | Q(is_superuser=True)


def notificar_evento_logistico(evento, pedido, actor=None, extra_info="", using=None):
    """
    Dispara notificaciones para Administrador(es) y Cliente (y Conductor cuando aplica)
    según la matriz de eventos del flujo logístico, sin duplicados.
    """
    db_alias = _resolver_db_alias(pedido, using)
    codigo = pedido.codigo_pedido
    cliente_usr = _resolver_usuario_en_db(pedido.cliente_usuario, db_alias=db_alias)
    admins = _obtener_administradores_activos(using=db_alias)

    try:
        link_pedido = reverse("pedidos:ver_pedido_admin", args=[codigo])
    except Exception:
        link_pedido = f"/pedidos/detalle/{codigo}/"

    if evento == "pago_aprobado":
        titulo_cliente = f"Pago aprobado - Pedido #CT-{codigo}"
        msg_cliente = (
            f"Tu pago para el pedido #CT-{codigo} fue aprobado. "
            f"El envío ha sido autorizado para despacho."
        )
        if cliente_usr:
            crear_notificacion_unica(
                cliente_usr,
                titulo_cliente,
                msg_cliente,
                tipo="success",
                link=link_pedido,
                using=db_alias,
            )

        titulo_admin = f"Despacho autorizado - Pedido #CT-{codigo}"
        msg_admin = (
            f"El pago del pedido #CT-{codigo} fue aprobado y el envío quedó en "
            f"estado «Autorizado Despacho» listo para asignar conductor y vehículo."
        )
        for adm in admins:
            crear_notificacion_unica(
                adm,
                titulo_admin,
                msg_admin,
                tipo="info",
                link=link_pedido,
                using=db_alias,
            )

    elif evento == "vehiculo_asignado":
        titulo_cliente = f"Conductor y vehículo asignados - Pedido #CT-{codigo}"
        msg_cliente = (
            f"Se asignó conductor y vehículo a tu pedido #CT-{codigo}. "
            f"{extra_info}".strip()
        )
        if cliente_usr:
            crear_notificacion_unica(
                cliente_usr,
                titulo_cliente,
                msg_cliente,
                tipo="info",
                link=link_pedido,
                using=db_alias,
            )

        titulo_admin = f"Asignación logística registrada - Pedido #CT-{codigo}"
        msg_admin = (
            f"El pedido #CT-{codigo} pasó a «Vehículo Asignado». {extra_info}".strip()
        )
        for adm in admins:
            crear_notificacion_unica(
                adm,
                titulo_admin,
                msg_admin,
                tipo="info",
                link=link_pedido,
                using=db_alias,
            )

        conductor_usr = _resolver_usuario_en_db(pedido.conductor_usuario, db_alias=db_alias)
        if conductor_usr and conductor_usr.rol == "conductor":
            titulo_cond = f"Nuevo envío asignado - Pedido #CT-{codigo}"
            msg_cond = (
                f"Tienes asignado el pedido #CT-{codigo} con destino a "
                f"{pedido.direccion_destino}. Revisa los materiales para alistamiento."
            )
            crear_notificacion_unica(
                conductor_usr,
                titulo_cond,
                msg_cond,
                tipo="info",
                link=link_pedido,
                using=db_alias,
            )

    elif evento == "en_ruta":
        nombre_actor = actor.nombre_mostrar if actor and hasattr(actor, "nombre_mostrar") else "El conductor"
        titulo_cliente = f"Pedido en ruta - Pedido #CT-{codigo}"
        msg_cliente = (
            f"Tu pedido #CT-{codigo} ya fue preparado, cargado al vehículo y se encuentra «En Ruta» "
            f"hacia {pedido.direccion_destino}."
        )
        if cliente_usr:
            crear_notificacion_unica(
                cliente_usr,
                titulo_cliente,
                msg_cliente,
                tipo="info",
                link=link_pedido,
                using=db_alias,
            )

        titulo_admin = f"Inicio de ruta confirmado - Pedido #CT-{codigo}"
        msg_admin = (
            f"{nombre_actor} confirmó la preparación e inició la ruta del pedido #CT-{codigo} "
            f"hacia {pedido.direccion_destino}."
        )
        for adm in admins:
            crear_notificacion_unica(
                adm,
                titulo_admin,
                msg_admin,
                tipo="info",
                link=link_pedido,
                using=db_alias,
            )

    elif evento == "entregado":
        nombre_actor = actor.nombre_mostrar if actor and hasattr(actor, "nombre_mostrar") else "El conductor"
        titulo_cliente = f"Pedido entregado - Pedido #CT-{codigo}"
        msg_cliente = (
            f"Tu pedido #CT-{codigo} ha sido entregado exitosamente en {pedido.direccion_destino}."
        )
        if cliente_usr:
            crear_notificacion_unica(
                cliente_usr,
                titulo_cliente,
                msg_cliente,
                tipo="success",
                link=link_pedido,
                using=db_alias,
            )

        titulo_admin = f"Entrega completada - Pedido #CT-{codigo}"
        msg_admin = (
            f"{nombre_actor} marcó el pedido #CT-{codigo} como «Entregado»."
        )
        for adm in admins:
            crear_notificacion_unica(
                adm,
                titulo_admin,
                msg_admin,
                tipo="success",
                link=link_pedido,
                using=db_alias,
            )

    elif evento == "pago_rechazado":
        pago = pedido.pago_actual
        try:
            link_pago = reverse("pagos:detalle_pago", args=[pago.pk]) if pago else link_pedido
        except Exception:
            link_pago = link_pedido
        motivo_txt = (extra_info or (pago.observaciones if pago else "") or "Revisión requerida").strip()
        titulo_cliente = f"Pago rechazado en pedido #CT-{codigo} — Tienes 12 horas para corregir"
        msg_cliente = (
            f"Tu pago o comprobante del pedido #CT-{codigo} no fue aprobado. "
            f"Motivo: {motivo_txt}. "
            f"Tienes un plazo máximo de 12 horas para corregir tu pago o enviar nuevamente el comprobante; "
            f"de lo contrario, o si el nuevo comprobante vuelve a ser rechazado, el pedido se cancelará automáticamente."
        )
        if cliente_usr:
            existente = (
                Notificacion.objects.using(db_alias)
                .filter(usuario=cliente_usr, titulo=titulo_cliente)
                .first()
            )
            if existente:
                existente.mensaje = msg_cliente
                existente.leida = False
                existente.tipo = "warning"
                existente.link = link_pago
                existente.save(using=db_alias, update_fields=["mensaje", "leida", "tipo", "link"])
                cache.delete(f"notif_user_{cliente_usr.pk}")
            else:
                crear_notificacion_unica(
                    cliente_usr,
                    titulo_cliente,
                    msg_cliente,
                    tipo="warning",
                    link=link_pago,
                    using=db_alias,
                )

    elif evento == "comprobante_reenviado":
        pago = pedido.pago_actual
        try:
            link_pago = reverse("pagos:detalle_pago", args=[pago.pk]) if pago else link_pedido
        except Exception:
            link_pago = link_pedido
        nombre_cliente = (
            cliente_usr.nombre_mostrar
            if cliente_usr and hasattr(cliente_usr, "nombre_mostrar")
            else "El cliente"
        )
        titulo_admin = f"Pago corregido · Nuevo comprobante enviado - Pedido #CT-{codigo}"
        msg_admin = (
            f"{nombre_cliente} corrigió el pago y cargó un nuevo comprobante para el pedido #CT-{codigo}. "
            f"Queda pendiente de revisión administrativa."
        )
        ahora = timezone.now()
        for adm in admins:
            existente = (
                Notificacion.objects.using(db_alias)
                .filter(usuario=adm, titulo__icontains=f"Pedido #CT-{codigo}")
                .filter(titulo__icontains="comprobante")
                .first()
            )
            if existente:
                existente.titulo = titulo_admin
                existente.mensaje = msg_admin
                existente.leida = False
                existente.tipo = "warning"
                existente.link = link_pago
                existente.fecha = ahora
                existente.save(
                    using=db_alias,
                    update_fields=["titulo", "mensaje", "leida", "tipo", "link", "fecha"],
                )
                cache.delete(f"notif_user_{adm.pk}")
            else:
                crear_notificacion_unica(
                    adm,
                    titulo_admin,
                    msg_admin,
                    tipo="warning",
                    link=link_pago,
                    using=db_alias,
                )

    elif evento == "pedido_cancelado":
        motivo_txt = (extra_info or pedido.motivo_cancelacion_display or "Cancelado").strip()
        titulo_cliente = f"Pedido cancelado - Pedido #CT-{codigo}"
        msg_cliente = (
            f"El pedido #CT-{codigo} ha sido cancelado. Motivo: {motivo_txt}."
        )
        if cliente_usr:
            crear_notificacion_unica(
                cliente_usr,
                titulo_cliente,
                msg_cliente,
                tipo="danger",
                link=link_pedido,
                using=db_alias,
            )


def validar_integridad_pedido_y_pago_para_despacho(
    pedido,
    pago=None,
    exigir_detalles=True,
    using=None,
):
    """
    Valida en el backend la integridad comercial y financiera antes de aprobar un pago
    o autorizar un pedido para despacho:
    - Que el pedido exista y no esté cancelado.
    - Que tenga productos asociados con cantidades > 0 y precios/subtotales coherentes.
    - Que el total del pedido sea > 0 y coincida con sus líneas.
    - Que el pago exista, su método sea válido, adjunte comprobante cuando aplica,
      y su importe coincida con el total del pedido.
    """
    if pedido is None or not getattr(pedido, "pk", None):
        raise ValidationError("El pedido especificado no existe.")

    db_alias = _resolver_db_alias(pedido, using)

    if pedido.estado == Pedido.CANCELADO:
        raise ValidationError(
            "No se puede aprobar el pago ni autorizar el despacho de un pedido cancelado."
        )

    detalles = list(pedido.detalles.using(db_alias).select_related("material").all())
    if exigir_detalles and not detalles:
        raise ValidationError(
            "No se puede autorizar un pedido sin productos asociados. "
            "Agrega los materiales al pedido antes de aprobar el pago o despachar."
        )

    suma_subtotales = Decimal("0.00")
    for det in detalles:
        if det.cantidad is None or det.cantidad <= 0:
            raise ValidationError(
                f"La cantidad del material «{getattr(det.material, 'nombre', det.pk)}» debe ser mayor que cero."
            )
        if det.precio_unitario is None or det.precio_unitario <= 0:
            raise ValidationError(
                f"El precio unitario del material «{getattr(det.material, 'nombre', det.pk)}» debe ser mayor que cero."
            )
        subtotal_calc = Decimal(det.cantidad) * det.precio_unitario
        if det.subtotal is not None and det.subtotal != subtotal_calc:
            raise ValidationError(
                f"El subtotal del material «{getattr(det.material, 'nombre', det.pk)}» ({det.subtotal}) "
                f"no coincide con cantidad × precio unitario ({subtotal_calc})."
            )
        suma_subtotales += subtotal_calc

    impuesto = pedido.impuesto or Decimal("0.00")
    descuento = pedido.descuento or Decimal("0.00")
    if detalles:
        total_esperado = suma_subtotales + impuesto - descuento
        if (pedido.total or Decimal("0.00")) == Decimal("0.00") and total_esperado > 0:
            pedido.subtotal = suma_subtotales
            pedido.total = total_esperado
            pedido.precio = total_esperado
            pedido.save(using=db_alias, update_fields=["subtotal", "total", "precio"])
        elif pedido.total != total_esperado:
            raise ValidationError(
                f"El total del pedido ({pedido.total}) no es coherente con la suma de sus productos ({total_esperado})."
            )
    else:
        total_esperado = pedido.total or pedido.precio or Decimal("0.00")

    if total_esperado <= 0 or (pedido.total or Decimal("0.00")) <= 0:
        raise ValidationError(
            "No se permite aprobar el pago ni autorizar para despacho un pedido con importe $0."
        )

    pago_obj = pago if pago is not None else pedido.pago_actual
    if pago_obj is not None:
        metodos_validos = {m[0] for m in Pago.METODOS}
        if pago_obj.metodo not in metodos_validos:
            raise ValidationError("El método de pago asociado al pedido no es válido.")
        if pago_obj.requiere_comprobante() and not pago_obj.comprobante:
            raise ValidationError(
                f"El método de pago {pago_obj.get_metodo_display()} requiere un comprobante válido adjunto."
            )
        if pago_obj.monto is None or pago_obj.monto <= 0:
            raise ValidationError("El importe del pago debe ser mayor que cero.")
        if pago_obj.monto != total_esperado:
            raise ValidationError(
                f"El importe del pago ({pago_obj.monto}) no coincide con el total del pedido ({total_esperado})."
            )

    return total_esperado


def obtener_o_crear_envio(pedido, using=None):
    """
    Obtiene o crea de forma idempotente el único registro Entrega (Envio) para el pedido.
    Nunca duplica envíos existentes.
    """
    db_alias = _resolver_db_alias(pedido, using)
    qs = select_for_update_if_supported(Entrega.objects.using(db_alias), db_alias)
    entrega = qs.filter(pedido=pedido).order_by("id_entrega").first()
    if entrega:
        return entrega, False

    entrega = Entrega.objects.using(db_alias).create(
        pedido=pedido,
        conductor=pedido.conductor if pedido.conductor_id else None,
        estado="pendiente",
        direccion_entrega=(pedido.direccion_destino or "Por definir").strip()[:200],
    )
    return entrega, True


def autorizar_despacho_por_pago(pedido, usuario_admin=None, exigir_detalles=True, using=None):
    """
    Transición: (Pago aprobado) -> Autorizado Despacho.
    Valida la integridad del pedido y del pago, crea el registro de Envío (Entrega) si no existe,
    establece el estado logístico inicial como «Autorizado Despacho» y genera las notificaciones
    correspondientes de forma idempotente.
    """
    db_alias = _resolver_db_alias(pedido, using)
    with transaction.atomic(using=db_alias):
        pedido_bloqueado = (
            select_for_update_if_supported(Pedido.objects.using(db_alias), db_alias)
            .get(pk=pedido.pk)
        )
        pago_actual = (
            Pago.objects.using(db_alias).filter(pedido=pedido_bloqueado).first()
        )
        if pago_actual is not None and pago_actual.estado != Pago.APROBADO:
            raise ValidationError(
                "No se puede autorizar el despacho de un pedido cuyo pago no esté aprobado."
            )
        validar_integridad_pedido_y_pago_para_despacho(
            pedido_bloqueado,
            pago=pago_actual,
            exigir_detalles=exigir_detalles,
            using=db_alias,
        )
        if pedido_bloqueado.estado == Pedido.PENDIENTE:
            pedido_bloqueado.transicionar(Pedido.AUTORIZADO_DESPACHO)
            pedido_bloqueado.save(using=db_alias, update_fields=["estado"])

        entrega, _ = obtener_o_crear_envio(pedido_bloqueado, using=db_alias)
        notificar_evento_logistico(
            "pago_aprobado",
            pedido_bloqueado,
            actor=usuario_admin,
            using=db_alias,
        )
        pedido.estado = pedido_bloqueado.estado
        pedido.total = pedido_bloqueado.total
        return entrega


def asignar_conductor_y_vehiculo(pedido, conductor_usuario_o_id, vehiculo_o_id, usuario_admin=None, using=None):
    """
    Transición: Autorizado Despacho (o reasignación en Vehículo Asignado) -> Vehículo Asignado.
    Valida conductor activo y libre, vehículo disponible y libre, usa select_for_update(),
    actualiza el registro único de Entrega y emite notificaciones.
    """
    db_alias = _resolver_db_alias(pedido, using)

    if not conductor_usuario_o_id:
        raise ValidationError("Debes seleccionar un conductor.")
    if not vehiculo_o_id:
        raise ValidationError("Debes seleccionar un vehículo.")

    conductor_raw_id = getattr(conductor_usuario_o_id, "pk", conductor_usuario_o_id)
    vehiculo_raw_id = getattr(vehiculo_o_id, "pk", vehiculo_o_id)

    try:
        conductor_raw_id = int(conductor_raw_id)
        vehiculo_raw_id = int(vehiculo_raw_id)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Identificadores de conductor o vehículo inválidos.") from exc

    with transaction.atomic(using=db_alias):
        orden = (
            select_for_update_if_supported(Pedido.objects.using(db_alias), db_alias)
            .get(pk=pedido.pk)
        )

        if orden.estado in (Pedido.EN_RUTA, Pedido.ENTREGADO, Pedido.CANCELADO):
            raise ValidationError(
                f"No se puede asignar conductor/vehículo a un pedido en estado {orden.get_estado_display()}."
            )

        if not orden.puede_despacharse:
            raise ValidationError(
                "El pedido aún no tiene autorización de despacho (el pago debe estar aprobado)."
            )

        # Resolver conductor (puede venir como Usuario.id o Conductor.pk)
        conductor_user = (
            select_for_update_if_supported(Usuario.objects.using(db_alias), db_alias)
            .filter(pk=conductor_raw_id, rol="conductor")
            .first()
        )
        conductor_perfil = None
        if conductor_user is not None:
            conductor_perfil = (
                Conductor.objects.using(db_alias).filter(usuario=conductor_user).first()
            )
        else:
            conductor_perfil = (
                select_for_update_if_supported(Conductor.objects.using(db_alias), db_alias)
                .select_related("usuario")
                .filter(pk=conductor_raw_id)
                .first()
            )
            if conductor_perfil:
                conductor_user = conductor_perfil.usuario

        if (
            conductor_user is None
            or not conductor_user.is_active
            or conductor_user.estado != "activo"
            or conductor_user.rol != "conductor"
        ):
            raise ValidationError("El conductor seleccionado no existe o se encuentra inactivo.")

        if conductor_perfil is None:
            conductor_perfil, _ = Conductor.ensure_for_user(conductor_user, using=db_alias)
        elif conductor_perfil.estado != "activo":
            raise ValidationError("El perfil del conductor seleccionado se encuentra inactivo.")

        # Un conductor puede recibir pedidos autorizados mientras aún no ha
        # iniciado una entrega. Se bloquea únicamente cuando ya está en ruta.
        envios_activos_conductor = (
            Entrega.objects.using(db_alias)
            .filter(
                Q(estado="en_ruta") | Q(pedido__estado=Pedido.EN_RUTA),
                conductor=conductor_perfil,
            )
            .exclude(pedido=orden)
        )
        pedido_en_ruta_legacy = (
            Pedido.objects.using(db_alias)
            .filter(estado=Pedido.EN_RUTA)
            .filter(Q(conductor=conductor_perfil) | Q(conductor_usuario_legacy=conductor_user))
            .exclude(pk=orden.pk)
            .exists()
        )
        if envios_activos_conductor.exists() or pedido_en_ruta_legacy:
            raise ValidationError(
                f"El conductor {conductor_user.nombre_mostrar} ya está en ruta con otro pedido."
            )

        # Resolver y bloquear vehículo
        vehiculo_bloqueado = (
            select_for_update_if_supported(Vehiculo.objects.using(db_alias), db_alias)
            .filter(pk=vehiculo_raw_id)
            .first()
        )
        if vehiculo_bloqueado is None:
            raise ValidationError("El vehículo seleccionado no existe.")

        entrega_existente = (
            select_for_update_if_supported(Entrega.objects.using(db_alias), db_alias)
            .filter(pedido=orden)
            .order_by("id_entrega")
            .first()
        )
        mismo_vehiculo_actual = (
            entrega_existente is not None and entrega_existente.vehiculo_id == vehiculo_bloqueado.pk
        )

        if vehiculo_bloqueado.estado != "disponible" and not mismo_vehiculo_actual:
            raise ValidationError(
                f"El vehículo {vehiculo_bloqueado.placa} no está disponible (estado actual: {vehiculo_bloqueado.get_estado_display()})."
            )

        envios_activos_vehiculo = (
            Entrega.objects.using(db_alias)
            .filter(
                vehiculo=vehiculo_bloqueado,
                estado__in=["pendiente", "en_ruta"],
                pedido__estado__in=[
                    Pedido.AUTORIZADO_DESPACHO,
                    Pedido.VEHICULO_ASIGNADO,
                    Pedido.EN_RUTA,
                ],
            )
            .exclude(pedido=orden)
        )
        if envios_activos_vehiculo.exists():
            raise ValidationError(
                f"El vehículo {vehiculo_bloqueado.placa} ya está ocupado en otro envío activo."
            )

        ahora = timezone.now()

        # Cerrar asignaciones previas en ConductorVehiculo y abrir la nueva
        ConductorVehiculo.objects.using(db_alias).filter(
            conductor=conductor_perfil,
            fecha_fin__isnull=True,
        ).update(fecha_fin=ahora)
        ConductorVehiculo.objects.using(db_alias).filter(
            vehiculo=vehiculo_bloqueado,
            fecha_fin__isnull=True,
        ).update(fecha_fin=ahora)
        ConductorVehiculo.objects.using(db_alias).create(
            conductor=conductor_perfil,
            vehiculo=vehiculo_bloqueado,
        )

        if entrega_existente:
            entrega = entrega_existente
            entrega.conductor = conductor_perfil
            entrega.conductor_usuario = conductor_user
            entrega.vehiculo = vehiculo_bloqueado
            entrega.fecha_asignacion = ahora
            entrega.direccion_entrega = (orden.direccion_destino or entrega.direccion_entrega or "Por definir")[:200]
            entrega.estado = "pendiente"
            entrega.save(using=db_alias)
        else:
            entrega = Entrega.objects.using(db_alias).create(
                pedido=orden,
                conductor=conductor_perfil,
                conductor_usuario=conductor_user,
                vehiculo=vehiculo_bloqueado,
                fecha_asignacion=ahora,
                estado="pendiente",
                direccion_entrega=(orden.direccion_destino or "Por definir")[:200],
            )

        orden.conductor = conductor_perfil
        orden.conductor_usuario_legacy = conductor_user
        if orden.estado != Pedido.VEHICULO_ASIGNADO:
            orden.transicionar(Pedido.VEHICULO_ASIGNADO)
            orden.save(
                using=db_alias,
                update_fields=["estado", "conductor", "conductor_usuario_legacy"],
            )
        else:
            orden.save(using=db_alias, update_fields=["conductor", "conductor_usuario_legacy"])

        info = f"Conductor: {conductor_user.nombre_mostrar} | Vehículo: {vehiculo_bloqueado.placa}."
        notificar_evento_logistico(
            "vehiculo_asignado",
            orden,
            actor=usuario_admin,
            extra_info=info,
            using=db_alias,
        )

        pedido.estado = orden.estado
        pedido.conductor = orden.conductor
        return entrega


def _verificar_permiso_operacion_envio(orden, entrega, usuario, db_alias="default"):
    """Verifica que el usuario sea administrador o el conductor asignado al envío."""
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        raise PermissionDenied("Usuario no autenticado.")

    es_admin = (
        getattr(usuario, "is_superuser", False)
        or getattr(usuario, "es_superadmin", False)
        or getattr(usuario, "rol", "") == "admin"
    )
    if es_admin:
        return True

    if getattr(usuario, "rol", "") != "conductor":
        raise PermissionDenied("No tienes permiso para gestionar este envío.")

    perfil_conductor = Conductor.objects.using(db_alias).filter(usuario__username=usuario.username).first()
    if perfil_conductor is None and getattr(usuario, "pk", None):
        perfil_conductor = Conductor.objects.using(db_alias).filter(usuario_id=usuario.pk).first()

    es_conductor_dueno = bool(
        (entrega and entrega.conductor_id and perfil_conductor and entrega.conductor_id == perfil_conductor.pk)
        or (entrega and entrega.conductor_usuario_id and entrega.conductor_usuario_id == usuario.pk)
        or (orden.conductor_id and perfil_conductor and orden.conductor_id == perfil_conductor.pk)
        or (orden.conductor_usuario_legacy_id and orden.conductor_usuario_legacy_id == usuario.pk)
    )
    if not es_conductor_dueno:
        raise PermissionDenied("Solo puedes gestionar los envíos que tienes asignados.")
    return True


def confirmar_preparacion_e_iniciar_ruta(entrega_o_pedido, usuario, using=None):
    """
    Transición: Vehículo Asignado -> En Ruta.
    Valida que el envío tenga conductor y vehículo asignados, que el usuario sea el conductor
    asignado o un administrador, registra fecha/hora de inicio de ruta y usuario que confirmó,
    pasa el vehículo a «en_ruta» y dispara las notificaciones.
    """
    db_alias = _resolver_db_alias(entrega_o_pedido, using)

    with transaction.atomic(using=db_alias):
        if isinstance(entrega_o_pedido, Entrega):
            entrega = (
                select_for_update_if_supported(Entrega.objects.using(db_alias), db_alias)
                .select_related("pedido", "conductor__usuario", "vehiculo")
                .get(pk=entrega_o_pedido.pk)
            )
            orden = (
                select_for_update_if_supported(Pedido.objects.using(db_alias), db_alias)
                .get(pk=entrega.pedido_id)
            )
        else:
            orden = (
                select_for_update_if_supported(Pedido.objects.using(db_alias), db_alias)
                .get(pk=entrega_o_pedido.pk)
            )
            entrega = (
                select_for_update_if_supported(Entrega.objects.using(db_alias), db_alias)
                .select_related("conductor__usuario", "vehiculo")
                .filter(pedido=orden)
                .order_by("id_entrega")
                .first()
            )

        _verificar_permiso_operacion_envio(orden, entrega, usuario, db_alias=db_alias)

        if entrega is None or not entrega.conductor_id or not entrega.vehiculo_id:
            raise ValidationError(
                "No se puede iniciar la ruta sin tener conductor y vehículo asignados."
            )

        if not orden.puede_despacharse:
            raise ValidationError(
                "No se puede iniciar la ruta de un pedido cuyo pago no ha sido aprobado."
            )

        if (
            orden.estado not in (Pedido.VEHICULO_ASIGNADO, Pedido.AUTORIZADO_DESPACHO)
            or entrega.estado != "pendiente"
        ):
            raise ValidationError(
                "Solo se puede confirmar la preparación e iniciar ruta cuando el pedido está autorizado para despacho con vehículo asignado."
            )

        ahora = timezone.now()
        actor_db = _resolver_usuario_en_db(usuario, db_alias=db_alias)

        entrega.fecha_salida = ahora
        entrega.confirmado_salida_por = actor_db
        entrega.transicionar("en_ruta")
        entrega.save(
            using=db_alias,
            update_fields=["estado", "fecha_salida", "confirmado_salida_por"],
        )

        orden.fecha_toma_entrega = ahora
        orden.transicionar(Pedido.EN_RUTA)
        orden.save(
            using=db_alias,
            update_fields=["estado", "fecha_toma_entrega"],
        )

        vehiculo = (
            select_for_update_if_supported(Vehiculo.objects.using(db_alias), db_alias)
            .get(pk=entrega.vehiculo_id)
        )
        if vehiculo.estado != "en_ruta":
            vehiculo.estado = "en_ruta"
            vehiculo.save(using=db_alias, update_fields=["estado"])

        notificar_evento_logistico(
            "en_ruta",
            orden,
            actor=actor_db or usuario,
            using=db_alias,
        )

        if isinstance(entrega_o_pedido, Entrega):
            entrega_o_pedido.estado = entrega.estado
            entrega_o_pedido.fecha_salida = entrega.fecha_salida
            entrega_o_pedido.confirmado_salida_por = entrega.confirmado_salida_por
            entrega_o_pedido.pedido.estado = orden.estado
        else:
            entrega_o_pedido.estado = orden.estado
            entrega_o_pedido.fecha_toma_entrega = orden.fecha_toma_entrega

        return entrega


def marcar_pedido_entregado(entrega_o_pedido, usuario, observacion="", using=None):
    """
    Transición: En Ruta -> Entregado.
    Exige que el pedido y el envío estén en «En Ruta», registra fecha/hora y usuario que marcó
    la entrega, libera la disponibilidad del vehículo y conductor, y dispara las notificaciones.
    """
    db_alias = _resolver_db_alias(entrega_o_pedido, using)

    with transaction.atomic(using=db_alias):
        if isinstance(entrega_o_pedido, Entrega):
            entrega = (
                select_for_update_if_supported(Entrega.objects.using(db_alias), db_alias)
                .select_related("pedido", "conductor__usuario", "vehiculo")
                .get(pk=entrega_o_pedido.pk)
            )
            orden = (
                select_for_update_if_supported(Pedido.objects.using(db_alias), db_alias)
                .get(pk=entrega.pedido_id)
            )
        else:
            orden = (
                select_for_update_if_supported(Pedido.objects.using(db_alias), db_alias)
                .get(pk=entrega_o_pedido.pk)
            )
            entrega = (
                select_for_update_if_supported(Entrega.objects.using(db_alias), db_alias)
                .select_related("conductor__usuario", "vehiculo")
                .filter(pedido=orden)
                .order_by("id_entrega")
                .first()
            )

        _verificar_permiso_operacion_envio(orden, entrega, usuario, db_alias=db_alias)

        if entrega is None or entrega.estado != "en_ruta" or orden.estado != Pedido.EN_RUTA:
            raise ValidationError(
                "No se puede marcar como entregado un pedido que no esté «En Ruta»."
            )

        ahora = timezone.now()
        actor_db = _resolver_usuario_en_db(usuario, db_alias=db_alias)

        if orden.fecha_toma_entrega and ahora < orden.fecha_toma_entrega:
            ahora = orden.fecha_toma_entrega

        entrega.fecha_entrega = ahora
        entrega.entregado_por = actor_db
        entrega.transicionar("entregado")
        entrega.save(
            using=db_alias,
            update_fields=["estado", "fecha_entrega", "entregado_por"],
        )

        orden.fecha_entrega_real = ahora
        orden.transicionar(Pedido.ENTREGADO)
        orden.save(
            using=db_alias,
            update_fields=["estado", "fecha_entrega_real"],
        )

        # Liberar vehículo si no tiene otras entregas activas
        if entrega.vehiculo_id:
            vehiculo = (
                select_for_update_if_supported(Vehiculo.objects.using(db_alias), db_alias)
                .filter(pk=entrega.vehiculo_id)
                .first()
            )
            otras_activas = (
                Entrega.objects.using(db_alias)
                .filter(vehiculo_id=entrega.vehiculo_id, estado="en_ruta")
                .exclude(pk=entrega.pk)
                .exists()
            )
            if vehiculo and not otras_activas:
                vehiculo.estado = "disponible"
                vehiculo.save(using=db_alias, update_fields=["estado"])

        # Liberar asignación activa en ConductorVehiculo si no tiene otros envíos pendientes/en_ruta
        if entrega.conductor_id:
            otros_envios_conductor = (
                Entrega.objects.using(db_alias)
                .filter(
                    conductor_id=entrega.conductor_id,
                    estado__in=["pendiente", "en_ruta"],
                    pedido__estado__in=[Pedido.VEHICULO_ASIGNADO, Pedido.EN_RUTA],
                )
                .exclude(pk=entrega.pk)
                .exists()
            )
            if not otros_envios_conductor:
                ConductorVehiculo.objects.using(db_alias).filter(
                    conductor_id=entrega.conductor_id,
                    fecha_fin__isnull=True,
                ).update(fecha_fin=ahora)

        observacion_limpia = (observacion or "").strip()
        if observacion_limpia and actor_db:
            Novedad.objects.using(db_alias).create(
                entrega=entrega,
                reportado_por=actor_db,
                tipo="observacion",
                descripcion=observacion_limpia,
                estado="cerrada",
                fecha_cierre=ahora,
            )

        notificar_evento_logistico(
            "entregado",
            orden,
            actor=actor_db or usuario,
            using=db_alias,
        )

        if isinstance(entrega_o_pedido, Entrega):
            entrega_o_pedido.estado = entrega.estado
            entrega_o_pedido.fecha_entrega = entrega.fecha_entrega
            entrega_o_pedido.entregado_por = entrega.entregado_por
            entrega_o_pedido.pedido.estado = orden.estado
        else:
            entrega_o_pedido.estado = orden.estado
            entrega_o_pedido.fecha_entrega_real = orden.fecha_entrega_real

        return entrega


def cancelar_envio_pedido(pedido, usuario, motivo="", revertir_stock=True, using=None):
    """
    Transición: Cualquier estado excepto Entregado -> Cancelado.
    Registra el motivo de cancelación, revierte stock si corresponde y libera vehículo y conductor.
    """
    db_alias = _resolver_db_alias(pedido, using)
    motivo_limpio = (motivo or "").strip()
    if not motivo_limpio:
        raise ValidationError("Debes indicar el motivo de la cancelación.")

    with transaction.atomic(using=db_alias):
        orden = (
            select_for_update_if_supported(Pedido.objects.using(db_alias), db_alias)
            .get(pk=pedido.pk)
        )
        if orden.estado == Pedido.ENTREGADO:
            raise ValidationError("No se puede cancelar un pedido que ya fue entregado.")
        if orden.estado == Pedido.CANCELADO:
            raise ValidationError("El pedido ya se encuentra cancelado.")

        actor_db = _resolver_usuario_en_db(usuario, db_alias=db_alias)
        ahora = timezone.now()

        if revertir_stock:
            revertir_stock_pedido(orden, actor_db or usuario, "Cancelación", using=db_alias)

        entrega = (
            select_for_update_if_supported(Entrega.objects.using(db_alias), db_alias)
            .filter(pedido=orden)
            .order_by("id_entrega")
            .first()
        )
        if entrega:
            entrega.motivo_cancelacion = motivo_limpio
            if entrega.estado != "cancelado":
                entrega.transicionar("cancelado")
                entrega.save(
                    using=db_alias,
                    update_fields=["estado", "motivo_cancelacion"],
                )
            else:
                entrega.save(using=db_alias, update_fields=["motivo_cancelacion"])

            if entrega.vehiculo_id:
                vehiculo = (
                    select_for_update_if_supported(Vehiculo.objects.using(db_alias), db_alias)
                    .filter(pk=entrega.vehiculo_id)
                    .first()
                )
                if vehiculo and vehiculo.estado == "en_ruta":
                    vehiculo.estado = "disponible"
                    vehiculo.save(using=db_alias, update_fields=["estado"])

            if entrega.conductor_id:
                ConductorVehiculo.objects.using(db_alias).filter(
                    conductor_id=entrega.conductor_id,
                    fecha_fin__isnull=True,
                ).update(fecha_fin=ahora)
        else:
            liberar_vehiculo_pedido(orden)

        responsable_txt = (
            actor_db.nombre_mostrar
            if actor_db and hasattr(actor_db, "nombre_mostrar")
            else getattr(usuario, "username", "Sistema")
        )
        fecha_txt = ahora.strftime("%d/%m/%Y %H:%M")
        prefijo_obs = f"[Cancelado el {fecha_txt} por {responsable_txt}: {motivo_limpio}]"
        orden.observacion_admin = (
            f"{orden.observacion_admin}\n{prefijo_obs}".strip()
            if orden.observacion_admin
            else prefijo_obs
        )[:2000]
        orden.transicionar(Pedido.CANCELADO)
        orden.save(
            using=db_alias,
            update_fields=["estado", "observacion_admin"],
        )

        notificar_evento_logistico(
            "pedido_cancelado",
            orden,
            actor=actor_db or usuario,
            extra_info=motivo_limpio,
            using=db_alias,
        )

        pedido.estado = orden.estado
        pedido.observacion_admin = orden.observacion_admin
        return entrega


def verificar_y_cancelar_pedidos_por_vencimiento_correccion_pago(pedido=None, using=None):
    """
    Cancela automáticamente (y envía al historial) los pedidos cuyo pago fue rechazado
    hace más de 12 horas sin que el cliente enviara un nuevo comprobante.
    Devuelve la lista de pedidos cancelados automáticamente.
    """
    db_alias = _resolver_db_alias(pedido, using)
    limite_vencimiento = timezone.now() - timedelta(hours=Pago.HORAS_PLAZO_CORRECCION)

    qs = (
        Pedido.objects.using(db_alias)
        .filter(
            estado=Pedido.PENDIENTE,
            pago__estado=Pago.RECHAZADO,
            pago__fecha_revision__isnull=False,
            pago__fecha_revision__lte=limite_vencimiento,
        )
        .select_related("pago", "usuario", "cliente__usuario")
    )
    if pedido is not None and getattr(pedido, "pk", None):
        qs = qs.filter(pk=pedido.pk)

    cancelados = []
    for ord_vencida in list(qs):
        motivo_auto = (
            "Cancelación automática: venció el plazo de 12 horas para corregir el pago "
            "o presentar nuevamente el comprobante. Debe realizar un nuevo pedido."
        )
        try:
            cancelar_envio_pedido(
                ord_vencida,
                usuario=None,
                motivo=motivo_auto,
                revertir_stock=True,
                using=db_alias,
            )
            cancelados.append(ord_vencida)
        except Exception:
            logger.warning(
                "No se pudo cancelar automáticamente el pedido vencido #%s",
                ord_vencida.codigo_pedido,
                exc_info=True,
            )

    if pedido is not None and cancelados:
        pedido.estado = Pedido.CANCELADO
        pedido.observacion_admin = cancelados[0].observacion_admin
    return cancelados


