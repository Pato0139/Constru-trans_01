import logging
import re
from datetime import datetime

from django.utils import timezone

logger = logging.getLogger(__name__)

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q, Sum
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalogo.models import Catalogo, Stock, UnidadMedida
from apps.catalogo.models import MaterialConstruccion as Material
from apps.pedidos.models import DetallePedido, Pedido
from apps.usuarios.models import Usuario
from config.db_preference import debe_usar_bd_remota
from config.db_utils import select_for_update_if_supported
from config.despacho import (
    CIUDADES_DESPACHO,
    ciudad_valida,
    construir_direccion_destino,
    separar_direccion_destino,
)
from config.security import (
    _respuesta_no_autorizada,
    obtener_ip,
    registrar_evento,
    registrar_warning,
    role_required,
)

from .models import Cliente


def pedidos_visibles_para_cliente(usuario_local, usuario_remoto):
    ids = [u.id for u in [usuario_local, usuario_remoto] if u]
    usernames = [u.username for u in [usuario_local, usuario_remoto] if u and u.username]

    return (
        Pedido.objects.filter(
            Q(usuario_id__in=ids)
            | Q(cliente__usuario_id__in=ids)
            | Q(usuario__username__in=usernames)
            | Q(cliente__usuario__username__in=usernames)
        )
        .select_related("cliente__usuario", "conductor")
        .prefetch_related("detalles", "entregas")
        .distinct()
        .order_by("-fecha_solicitud")
    )


def _contexto_formulario_pedido(**extra):
    return {"ciudades_despacho": CIUDADES_DESPACHO, **extra}


def _obtener_alias_db():
    return "remota" if debe_usar_bd_remota() else "default"


def _obtener_usuario_local(usuario):
    if usuario._state.db == "default":
        return usuario

    usuario_local, _ = Usuario.objects.using("default").update_or_create(
        username=usuario.username,
        defaults={
            "password": usuario.password,
            "nombres": usuario.nombres,
            "apellidos": usuario.apellidos,
            "email": usuario.email,
            "telefono": usuario.telefono,
            "documento": usuario.documento,
            "rol": usuario.rol,
            "tipo_documento": usuario.tipo_documento,
            "estado": usuario.estado,
            "foto_perfil": usuario.foto_perfil,
            "sincronizado": True,
            "is_superuser": usuario.is_superuser,
            "is_staff": usuario.is_staff,
            "is_active": usuario.is_active,
            "date_joined": usuario.date_joined,
            "last_login": usuario.last_login,
        },
    )
    return usuario_local


def _obtener_cliente_local(usuario_local, using="default"):
    cliente_local, _ = Cliente.ensure_for_user(
        usuario_local,
        using=using,
        defaults={"direccion": "Por definir"},
    )
    return cliente_local


def _obtener_catalogo_local(catalogo):
    if not catalogo:
        return None
    if catalogo._state.db == "default":
        return catalogo

    catalogo_local, _ = Catalogo.objects.using("default").update_or_create(
        pk=catalogo.pk,
        defaults={
            "nombre_empresa": catalogo.nombre_empresa,
        },
    )
    return catalogo_local


def _obtener_unidad_medida_local(unidad):
    if unidad._state.db == "default":
        return unidad

    unidad_local, _ = UnidadMedida.objects.using("default").update_or_create(
        id_unidad=unidad.id_unidad,
        defaults={
            "codigo": unidad.codigo,
            "nombre": unidad.nombre,
            "abreviatura": unidad.abreviatura,
            "descripcion": unidad.descripcion,
            "activa": unidad.activa,
            "orden": unidad.orden,
        },
    )
    return unidad_local


def _obtener_material_local(material_id):
    try:
        return Material.objects.using("default").get(pk=material_id)
    except Material.DoesNotExist:
        remote_material = Material.objects.using("remota").get(pk=material_id)
        catalogo_local = (
            _obtener_catalogo_local(remote_material.catalogo) if remote_material.catalogo else None
        )
        unidad_local = _obtener_unidad_medida_local(remote_material.unidad_medida)
        material_local, _ = Material.objects.using("default").update_or_create(
            pk=remote_material.pk,
            defaults={
                "catalogo": catalogo_local,
                "nombre": remote_material.nombre,
                "unidad_medida": unidad_local,
                "descripcion": remote_material.descripcion,
                "precio_referencia": remote_material.precio_referencia,
                "sincronizado": True,
            },
        )
        return material_local


def _es_dueno_pedido(pedido, usuario_remoto, usuario_local):
    if not pedido or pedido.usuario_id is None:
        return False

    if usuario_local and pedido.usuario_id == usuario_local.id:
        return True
    if usuario_remoto and pedido.usuario_id == usuario_remoto.id:
        return True

    try:
        candidato = Usuario.objects.using("default").get(pk=pedido.usuario_id)
        return candidato.username == usuario_local.username
    except Usuario.DoesNotExist:
        pass

    try:
        candidato = Usuario.objects.using("remota").get(pk=pedido.usuario_id)
        return candidato.username == usuario_remoto.username
    except Usuario.DoesNotExist:
        pass

    return False


def parse_fecha_entrega(value):
    if not value:
        return None
    value = value.strip()

    for candidate in [value, value.replace(" ", "T")]:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass

    normalized = value.lower()
    normalized = re.sub(r"[\.]+", "/", normalized)
    normalized = normalized.replace("-", "/")
    normalized = normalized.replace(",", " ")
    normalized = normalized.replace(" a.m.", " am").replace(" p.m.", " pm")
    normalized = normalized.replace(" a.m", " am").replace(" p.m", " pm")
    normalized = normalized.replace("am", " am").replace("pm", " pm")
    normalized = re.sub(r"\s+", " ", normalized).strip()

    formats = [
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%Y",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d %I:%M %p",
        "%Y/%m/%Y",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            if fmt in ("%d/%m/%Y", "%Y/%m/%d"):
                dt = dt.replace(hour=0, minute=0)
            return dt
        except ValueError:
            continue

    return None


def _es_fecha_pasada(fecha_str):
    """
    Verifica si el valor de fecha proporcionado corresponde a una fecha
    anterior a la fecha actual (hoy). Regresa True si es pasado.
    """
    fecha = parse_fecha_entrega(fecha_str)
    if fecha is None:
        return False
    today = timezone.localtime(timezone.now()).date()
    return fecha.date() < today


def _normalizar_items_pedido(materiales_ids, cantidades):
    if not materiales_ids or len(materiales_ids) > 50:
        return None, "El pedido debe incluir entre 1 y 50 materiales."
    if len(materiales_ids) != len(cantidades):
        return None, "Error en los datos del formulario. Intenta nuevamente."

    items = []
    ids_vistos = set()
    for material_id, cantidad_raw in zip(materiales_ids, cantidades, strict=True):
        if not material_id or not material_id.isdecimal():
            return None, "El pedido contiene materiales inválidos o repetidos."
        material_pk = int(material_id)
        if material_pk in ids_vistos:
            return None, "El pedido contiene materiales inválidos o repetidos."
        if not cantidad_raw or not cantidad_raw.isdecimal():
            return None, "Las cantidades deben ser números enteros positivos."

        cantidad = int(cantidad_raw)
        if not 1 <= cantidad <= 100000:
            return None, "Cada cantidad debe estar entre 1 y 100000."

        ids_vistos.add(material_pk)
        items.append((material_pk, cantidad))
    return items, None


@role_required(["cliente"])
def panel_cliente(request):
    try:
        usuario_remoto = request.user.usuario
        usuario = _obtener_usuario_local(usuario_remoto)
        cliente, created = Cliente.ensure_for_user(usuario_remoto)
    except (Usuario.DoesNotExist, AttributeError):
        if request.user.is_superuser:
            return redirect("usuarios:panel")
        logout(request)
        messages.error(request, "Su cuenta no tiene un perfil de usuario asignado.")
        return redirect("usuarios:login")
    except Exception as e:
        messages.error(request, f"Error al cargar el panel: {str(e)}")
        return redirect("usuarios:login")

    pedidos = pedidos_visibles_para_cliente(usuario, usuario_remoto)
    context = {
        "pedidos_activos": pedidos.filter(estado="pendiente").count(),
        "entregas": pedidos.filter(estado="entregado").count(),
        "total_gastado": pedidos.aggregate(total=Sum("total"))["total"] or 0,
        "ultimos_pedidos": pedidos[:5],
    }
    return render(request, "clientes/lista.html", context)


@role_required(["cliente"])
def mis_pedidos(request):
    try:
        usuario_remoto = request.user.usuario if hasattr(request.user, "usuario") else request.user
        usuario = _obtener_usuario_local(usuario_remoto)
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")

    # Solo pedidos activos (no en estado final: entregado o cancelado)
    pedidos = (
        pedidos_visibles_para_cliente(usuario, usuario_remoto)
        .exclude(estado__in=["entregado", "cancelado"])
        .select_related("pago")
        .prefetch_related("detalles__material")
    )

    # Get filter parameters
    destino = request.GET.get("destino", "")
    estado = request.GET.get("estado", "")
    q = request.GET.get("q", "")

    # Apply filters
    if destino:
        pedidos = pedidos.filter(direccion_destino__icontains=destino)
    if estado:
        pedidos = pedidos.filter(estado=estado)
    if q:
        pedidos = pedidos.filter(
            Q(codigo_pedido__icontains=q)
            | Q(direccion_destino__icontains=q)
            | Q(estado__icontains=q)
            | Q(direccion_origen__icontains=q)
        )

    # Prepare filter fields
    filter_fields = [
        {"type": "text", "name": "q", "placeholder": "Buscar...", "value": q, "size": "3"},
        {
            "type": "text",
            "name": "destino",
            "placeholder": "Destino",
            "value": destino,
            "size": "3",
        },
        {
            "type": "select",
            "name": "estado",
            "placeholder": "Estado (Todos)",
            "value": estado,
            "size": "3",
            "options": [
                {"value": "pendiente", "label": "Pendiente"},
                {"value": "autorizado_despacho", "label": "Autorizado Despacho"},
                {"value": "vehiculo_asignado", "label": "Vehículo Asignado"},
                {"value": "en_ruta", "label": "En Ruta"},
            ],
        },
    ]

    has_filters = any([destino, estado, q])
    context = {
        "pedidos": pedidos,
        "filter_fields": filter_fields,
        "has_filters": has_filters,
        "q": q,
        "destino": destino,
        "estado": estado,
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "clientes/_mis_pedidos_body.html", {"pedidos": pedidos})

    return render(request, "clientes/mis_pedidos.html", context)


@role_required(["cliente"])
def perfil_cliente(request):
    try:
        usuario_remoto = request.user.usuario if hasattr(request.user, "usuario") else request.user
        usuario = _obtener_usuario_local(usuario_remoto)
    except (Usuario.DoesNotExist, AttributeError):
        logout(request)
        return redirect("usuarios:login")

    pedidos = pedidos_visibles_para_cliente(usuario, usuario_remoto)

    context = {
        "cliente": usuario,
        "total_pedidos": pedidos.count(),
        "pedidos_pendientes": pedidos.filter(estado="pendiente").count(),
        "en_ruta": pedidos.filter(estado="en_ruta").count(),
        "total_invertido": pedidos.aggregate(total=Sum("total"))["total"] or 0,
    }

    return render(request, "clientes/detalle.html", context)


@role_required(["cliente"])
def seguimiento_pedidos(request):
    try:
        usuario_remoto = request.user.usuario if hasattr(request.user, "usuario") else request.user
        usuario = _obtener_usuario_local(usuario_remoto)
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")

    messages.info(request, "El seguimiento se consulta directamente desde el detalle de cada pedido.")
    return redirect("clientes:mis_pedidos")


@role_required(["cliente"])
def historial_pedidos(request):
    try:
        usuario_remoto = request.user.usuario if hasattr(request.user, "usuario") else request.user
        usuario = _obtener_usuario_local(usuario_remoto)
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")

    q = request.GET.get("q", "").strip()
    fecha = request.GET.get("fecha", "").strip()
    estado = request.GET.get("estado", "").strip()

    # Historial: pedidos que ya finalizaron (entregado o cancelado)
    pedidos = (
        pedidos_visibles_para_cliente(usuario, usuario_remoto)
        .filter(estado__in=["entregado", "cancelado"])
        .prefetch_related("detalles__material")
    )

    if q:
        pedidos = pedidos.filter(
            Q(codigo_pedido__icontains=q)
            | Q(detalles__material__nombre__icontains=q)
            | Q(direccion_destino__icontains=q)
        ).distinct()
    if fecha:
        pedidos = pedidos.filter(
            Q(fecha_entrega_real__date=fecha) | Q(fecha_solicitud__date=fecha)
        )
    if estado in ["entregado", "cancelado"]:
        pedidos = pedidos.filter(estado=estado)

    context = {
        "pedidos": pedidos,
        "q": q,
        "fecha": fecha,
        "estado": estado,
        "has_filters": bool(q or fecha or estado),
    }

    return render(request, "clientes/historial.html", context)


@role_required(["cliente"])
def crear_pedido(request):
    usuario_remoto = request.user.usuario if hasattr(request.user, "usuario") else request.user
    usuario_local = _obtener_usuario_local(usuario_remoto)

    _cliente_local = _obtener_cliente_local(usuario_local)
    materiales = Material.objects.all()

    if request.method == "POST":
        materiales_ids = request.POST.getlist("material_id[]")
        cantidades = request.POST.getlist("cantidad[]")
        ciudad = request.POST.get("ciudad", "").strip()
        direccion_detalle = request.POST.get("direccion_detalle", "").strip()
        direccion = construir_direccion_destino(ciudad, direccion_detalle)
        fecha_entrega_raw = request.POST.get("fecha_entrega")
        fecha_entrega = parse_fecha_entrega(fecha_entrega_raw)

        if fecha_entrega_raw and not fecha_entrega:
            if _es_fecha_pasada(fecha_entrega_raw):
                messages.error(
                    request,
                    "Solo se aceptan fechas a partir de hoy en adelante.",
                )
            else:
                messages.error(
                    request,
                    "Formato de fecha inválido. Usa DD/MM/YYYY HH:MM, DD-MM-YYYY HH:MM o 2026-12-31 15:30.",
                )
            return render(
                request,
                "clientes/form.html",
                _contexto_formulario_pedido(
                    materiales=materiales,
                    action="crear",
                    fecha_entrega=fecha_entrega_raw,
                    ciudad=ciudad,
                    direccion_detalle=direccion_detalle,
                ),
            )

        if not materiales_ids or not ciudad or not direccion_detalle:
            messages.error(
                request, "Agrega materiales, selecciona la ciudad de destino e indica la dirección."
            )
            return render(
                request,
                "clientes/form.html",
                _contexto_formulario_pedido(
                    materiales=materiales,
                    action="crear",
                    fecha_entrega=fecha_entrega_raw,
                    ciudad=ciudad,
                    direccion_detalle=direccion_detalle,
                ),
            )

        if not ciudad_valida(ciudad):
            messages.error(
                request, "La ciudad seleccionada no está dentro de la zona de despacho autorizada."
            )
            return render(
                request,
                "clientes/form.html",
                _contexto_formulario_pedido(
                    materiales=materiales,
                    action="crear",
                    fecha_entrega=fecha_entrega_raw,
                    ciudad=ciudad,
                    direccion_detalle=direccion_detalle,
                ),
            )

        items, error_items = _normalizar_items_pedido(materiales_ids, cantidades)
        if error_items:
            messages.error(request, error_items)
            return render(
                request,
                "clientes/form.html",
                _contexto_formulario_pedido(
                    materiales=materiales,
                    action="crear",
                    fecha_entrega=fecha_entrega_raw,
                    ciudad=ciudad,
                    direccion_detalle=direccion_detalle,
                ),
            )

        db_alias = _obtener_alias_db()
        usuario_para_pedido = usuario_remoto if db_alias == "remota" else usuario_local
        cliente_para_pedido = _obtener_cliente_local(usuario_para_pedido, using=db_alias)

        try:
            with transaction.atomic(using=db_alias):
                total_general = 0
                nuevo_pedido = Pedido.objects.using(db_alias).create(
                    usuario=usuario_para_pedido,
                    cliente=cliente_para_pedido,
                    direccion_origen="Bodega Central",
                    direccion_destino=direccion,
                    estado="pendiente",
                    fecha_entrega_programada=fecha_entrega if fecha_entrega else None,
                )

                for m_id, cantidad in items:
                    material = _obtener_material_local(m_id)
                    try:
                        stock_obj = select_for_update_if_supported(
                            Stock.objects.using(db_alias),
                            db_alias,
                        ).get(material=material)
                    except Stock.DoesNotExist:
                        stock_obj = Stock.objects.using(db_alias).create(
                            material=material, cantidad_actual=0
                        )

                    try:
                        cantidad = int(cantidad)
                    except (ValueError, TypeError) as err:
                        raise ValueError(f"Cantidad inválida para {material.nombre}") from err

                    if cantidad <= 0:
                        raise ValueError(f"La cantidad para {material.nombre} debe ser mayor a 0.")

                    if stock_obj.cantidad_actual < cantidad:
                        raise ValueError(
                            f"Stock insuficiente para {material.nombre}. "
                            f"Quedan {stock_obj.cantidad_actual}."
                        )

                    precio_unitario = material.precio
                    total_item = precio_unitario * cantidad
                    total_general += total_item

                    DetallePedido.objects.using(db_alias).create(
                        pedido=nuevo_pedido,
                        material=material,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                    )

                    stock_obj.cantidad_actual = F("cantidad_actual") - cantidad
                    stock_obj.save(using=db_alias)

            messages.success(request, f"Pedido #{nuevo_pedido.codigo_pedido} creado correctamente. Registra el pago para habilitar el despacho.")
            return redirect("pagos:registrar_pago_pedido", pedido_id=nuevo_pedido.codigo_pedido)

        except ValueError as e:
            messages.error(request, str(e))
            return render(
                request,
                "clientes/form.html",
                _contexto_formulario_pedido(
                    materiales=materiales,
                    action="crear",
                ),
            )
        except Exception:
            logger.exception("Error inesperado al crear pedido")
            messages.error(
                request,
                "Ocurrió un error inesperado al procesar el pedido. Por favor intenta nuevamente.",
            )
            return render(
                request,
                "clientes/form.html",
                _contexto_formulario_pedido(
                    materiales=materiales,
                    action="crear",
                ),
            )

    return render(
        request,
        "clientes/form.html",
        _contexto_formulario_pedido(
            materiales=materiales,
            action="crear",
        ),
    )


@role_required(["cliente", "admin"])
def editar_pedido(request, id):
    usuario_remoto = request.user.usuario
    db_alias = _obtener_alias_db()
    pedido = get_object_or_404(Pedido.objects.using(db_alias), codigo_pedido=id)

    is_super = getattr(request.user, "is_superuser", False) or getattr(
        request.user, "es_superadmin", False
    )
    es_admin = is_super or usuario_remoto.rol == "admin"
    usuario = _obtener_usuario_local(usuario_remoto)
    es_dueno = _es_dueno_pedido(pedido, usuario_remoto, usuario)

    # Validación de propiedad ANTES de cualquier render
    if not (es_admin or es_dueno):
        ip = obtener_ip(request)
        registrar_warning(ip)
        registrar_evento(
            request,
            "role_violation",
            gravedad="high",
            detalles={
                "causa": "editar_pedido_ajeno",
                "codigo_pedido": pedido.codigo_pedido,
                "cliente_pedido_id": pedido.cliente_id,
                "operacion": "editar",
            },
        )
        return _respuesta_no_autorizada(
            request,
            detalles={
                "rol_requerido": ["admin"],
                "permiso_alternativo": "propietario del pedido",
                "codigo_pedido": pedido.codigo_pedido,
            },
        )

    detalle_total = sum(d.subtotal for d in pedido.detalles.using(db_alias).all())
    if pedido.total != detalle_total or pedido.precio != detalle_total:
        pedido.total = detalle_total
        pedido.precio = detalle_total
        pedido.save(using=db_alias)

    materiales = Material.objects.all()

    if pedido.estado != "pendiente":
        messages.error(
            request,
            "El pedido ya no se puede modificar (estado actual: {}).".format(pedido.estado),
        )
        if es_admin:
            return redirect("pedidos:lista_pedidos_admin")
        return redirect("clientes:mis_pedidos")

    if request.method == "POST":
        materiales_ids = request.POST.getlist("material_id[]")
        cantidades = request.POST.getlist("cantidad[]")
        ciudad = request.POST.get("ciudad", "").strip()
        direccion_detalle = request.POST.get("direccion_detalle", "").strip()
        direccion = construir_direccion_destino(ciudad, direccion_detalle)
        fecha_entrega_raw = request.POST.get("fecha_entrega")
        fecha_entrega = parse_fecha_entrega(fecha_entrega_raw)

        if fecha_entrega_raw and not fecha_entrega:
            if _es_fecha_pasada(fecha_entrega_raw):
                messages.error(
                    request,
                    "Solo se aceptan fechas a partir de hoy en adelante.",
                )
            else:
                messages.error(
                    request,
                    "Formato de fecha inválido. Usa DD/MM/YYYY HH:MM, DD-MM-YYYY HH:MM o 2026-12-31 15:30.",
                )
            return render(
                request,
                "clientes/form.html",
                _contexto_formulario_pedido(
                    orden=pedido,
                    materiales=materiales,
                    action="editar",
                    fecha_entrega=fecha_entrega_raw,
                    ciudad=ciudad,
                    direccion_detalle=direccion_detalle,
                ),
            )

        if not materiales_ids or not ciudad or not direccion_detalle:
            messages.error(
                request, "Datos incompletos: materiales, ciudad y dirección son obligatorios."
            )
            return render(
                request,
                "clientes/form.html",
                _contexto_formulario_pedido(
                    orden=pedido,
                    materiales=materiales,
                    action="editar",
                    fecha_entrega=fecha_entrega_raw,
                    ciudad=ciudad,
                    direccion_detalle=direccion_detalle,
                ),
            )

        if not ciudad_valida(ciudad):
            messages.error(
                request, "La ciudad seleccionada no está dentro de la zona de despacho autorizada."
            )
            return render(
                request,
                "clientes/form.html",
                _contexto_formulario_pedido(
                    orden=pedido,
                    materiales=materiales,
                    action="editar",
                    fecha_entrega=fecha_entrega_raw,
                    ciudad=ciudad,
                    direccion_detalle=direccion_detalle,
                ),
            )

        items, error_items = _normalizar_items_pedido(materiales_ids, cantidades)
        if error_items:
            messages.error(request, error_items)
            return render(
                request,
                "clientes/form.html",
                _contexto_formulario_pedido(
                    orden=pedido,
                    materiales=materiales,
                    action="editar",
                    fecha_entrega=fecha_entrega_raw,
                    ciudad=ciudad,
                    direccion_detalle=direccion_detalle,
                ),
            )

        try:
            with transaction.atomic(using=db_alias):
                for detalle in pedido.detalles.using(db_alias).all():
                    try:
                        stock_obj = select_for_update_if_supported(
                            Stock.objects.using(db_alias),
                            db_alias,
                        ).get(material=detalle.material)
                    except Stock.DoesNotExist:
                        stock_obj = Stock.objects.using(db_alias).create(
                            material=detalle.material,
                            cantidad_actual=0,
                        )
                    stock_obj.cantidad_actual = F("cantidad_actual") + detalle.cantidad
                    stock_obj.save(using=db_alias)

                pedido.detalles.using(db_alias).all().delete()

                total_general = 0
                for m_id, cantidad in items:
                    material = _obtener_material_local(m_id)
                    try:
                        stock_obj = select_for_update_if_supported(
                            Stock.objects.using(db_alias),
                            db_alias,
                        ).get(material=material)
                    except Stock.DoesNotExist:
                        stock_obj = Stock.objects.using(db_alias).create(
                            material=material, cantidad_actual=0
                        )
                    if stock_obj.cantidad_actual < cantidad:
                        raise ValueError(f"Stock insuficiente para {material.nombre}")

                    DetallePedido.objects.using(db_alias).create(
                        pedido=pedido,
                        material=material,
                        cantidad=cantidad,
                        precio_unitario=material.precio,
                    )

                    stock_obj.cantidad_actual = F("cantidad_actual") - cantidad
                    stock_obj.save(using=db_alias)
                    total_general += material.precio * cantidad

                pedido.direccion_destino = direccion
                pedido.fecha_entrega_programada = fecha_entrega if fecha_entrega else None
                pedido.save(using=db_alias)
                pedido.calcular_total(using=db_alias)

            messages.success(request, f"Pedido #{pedido.codigo_pedido} actualizado correctamente.")
            if es_admin:
                return redirect("pedidos:lista_pedidos_admin")
            return redirect("clientes:mis_pedidos")

        except Exception:
            logger.exception("Error al actualizar el pedido %s", id)
            messages.error(
                request,
                "Ocurrió un error inesperado al actualizar el pedido. Por favor intenta nuevamente.",
            )

    ciudad_ini, detalle_ini = separar_direccion_destino(pedido.direccion_destino)
    return render(
        request,
        "clientes/form.html",
        _contexto_formulario_pedido(
            orden=pedido,
            materiales=materiales,
            action="editar",
            ciudad=ciudad_ini,
            direccion_detalle=detalle_ini,
        ),
    )


@role_required(["cliente", "admin"])
@require_POST
def cancelar_pedido(request, id):
    pedido = get_object_or_404(Pedido, codigo_pedido=id)

    usuario_remoto = request.user.usuario
    is_super = getattr(request.user, "is_superuser", False) or getattr(
        request.user, "es_superadmin", False
    )
    es_admin = is_super or usuario_remoto.rol == "admin"
    usuario = _obtener_usuario_local(usuario_remoto)
    es_dueno = _es_dueno_pedido(pedido, usuario_remoto, usuario)

    if not (es_admin or es_dueno):
        ip = obtener_ip(request)
        registrar_warning(ip)
        registrar_evento(
            request,
            "role_violation",
            gravedad="high",
            detalles={
                "causa": "cancelar_pedido_ajeno",
                "codigo_pedido": pedido.codigo_pedido,
                "cliente_pedido_id": pedido.cliente_id,
                "operacion": "cancelar",
            },
        )
        return _respuesta_no_autorizada(
            request,
            detalles={
                "rol_requerido": ["admin"],
                "permiso_alternativo": "propietario del pedido",
                "codigo_pedido": pedido.codigo_pedido,
            },
        )

    if pedido.estado != "pendiente":
        messages.error(request, "Solo se pueden cancelar pedidos en estado pendiente.")
        if es_admin:
            return redirect("pedidos:lista_pedidos_admin")
        return redirect("clientes:mis_pedidos")

    db_alias = _obtener_alias_db()
    try:
        with transaction.atomic(using=db_alias):
            for detalle in pedido.detalles.using(db_alias).all():
                try:
                    material_obj = detalle.material
                except ObjectDoesNotExist:
                    material_obj = None

                if material_obj is not None:
                    try:
                        stock_obj = select_for_update_if_supported(
                            Stock.objects.using(db_alias),
                            db_alias,
                        ).get(material=material_obj)
                    except Stock.DoesNotExist:
                        stock_obj = Stock.objects.using(db_alias).create(
                            material=material_obj, cantidad_actual=0
                        )
                    stock_obj.cantidad_actual = F("cantidad_actual") + detalle.cantidad
                    stock_obj.save(using=db_alias)

            pedido.estado = "cancelado"
            pedido.save(using=db_alias, update_fields=["estado"])

            from config.utils import registrar_actividad

            comentario = (
                f"Pedido #{pedido.codigo_pedido} cancelado por {'admin' if es_admin else 'cliente'}"
            )
            registrar_actividad(
                request,
                "cancelar_pedido",
                "pedidos",
                pedido.codigo_pedido,
                comentario,
            )

        messages.warning(
            request,
            f"Pedido #{pedido.codigo_pedido} ha sido cancelado y el stock ha sido devuelto.",
        )
    except Exception:
        logger.exception("Error al cancelar el pedido %s", id)
        messages.error(
            request,
            "Ocurrió un error inesperado al cancelar el pedido. Por favor intenta nuevamente.",
        )

    if es_admin:
        return redirect("pedidos:lista_pedidos_admin")
    return redirect("clientes:mis_pedidos")


# =====================================================================
# VISTAS DE ADMINISTRACIÓN DE CLIENTES
# =====================================================================

@role_required(["admin"])
def lista_clientes(request):
    clientes = Usuario.objects.filter(rol="cliente").select_related("perfil_cliente").order_by("-date_joined")
    

@login_required
def lista_clientes(request):
    if request.user.rol != "admin":
        messages.error(request, "No tienes permisos para ver el listado de clientes.")
        return redirect("usuarios:panel")

    clientes = (
        Usuario.objects.filter(rol="cliente")
        .select_related("perfil_cliente")
        .order_by("-date_joined")
    )

    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "").strip()

    if q:
        clientes = clientes.filter(
            Q(nombres__icontains=q)
            | Q(apellidos__icontains=q)
            | Q(documento__icontains=q)
            | Q(email__icontains=q)
            | Q(telefono__icontains=q)
            | Q(username__icontains=q)
        )
    if estado:
        clientes = clientes.filter(estado=estado)

    has_filters = bool(q or estado)
    total_resultados = clientes.count()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(
            request,
            "clientes/_admin_lista_body.html",
            {
                "clientes": clientes,
                "has_filters": has_filters,
            },
        )

    context = {
        "clientes": clientes,
        "q": q,
        "estado": estado,
        "has_filters": has_filters,
        "total_resultados": total_resultados,
    }
    return render(request, "clientes/admin_lista.html", context)


@role_required(["admin"])
def detalle_cliente(request, id):
        
    if request.user.rol != "admin":
        messages.error(request, "No tienes permisos para ver este perfil.")
        return redirect("usuarios:panel")

    usuario = get_object_or_404(Usuario, id=id, rol="cliente")
    cliente, _ = Cliente.ensure_for_user(usuario)
    pedidos = Pedido.objects.filter(usuario=usuario).order_by("-fecha_solicitud")

    context = {
        "usuario_cliente": usuario,
        "cliente": cliente,
        "pedidos": pedidos,
        "total_gastado": pedidos.aggregate(total=Sum("total"))["total"] or 0,
        "pedidos_entregados": pedidos.filter(estado="entregado").count(),
    }
    return render(request, "clientes/admin_detalle.html", context)


@role_required(["admin"])
def editar_cliente(request, id):
        
    if request.user.rol != "admin":
        messages.error(request, "No tienes permisos para editar este cliente.")
        return redirect("usuarios:panel")

    usuario = get_object_or_404(Usuario, id=id, rol="cliente")
    cliente, _ = Cliente.ensure_for_user(usuario)

    if request.method == "POST":
        tipo_cliente = request.POST.get("tipo_cliente", cliente.tipo_cliente)
        estado = request.POST.get("estado", "")
        if (
            tipo_cliente not in dict(Cliente.TIPOS_CLIENTE)
            or (estado and estado not in dict(Usuario.ESTADO_USUARIO))
        ):
            messages.error(request, "El tipo de cliente o estado seleccionado no es válido.")
            return render(
                request,
                "clientes/admin_editar.html",
                {
                    "usuario_cliente": usuario,
                    "cliente": cliente,
                    "tipos_cliente": Cliente.TIPOS_CLIENTE,
                },
                status=400,
            )

        cliente.direccion_principal = request.POST.get("direccion_principal", cliente.direccion_principal)
        cliente.direccion_principal = request.POST.get(
            "direccion_principal", cliente.direccion_principal
        )
        cliente.direccion = request.POST.get("direccion", cliente.direccion)
        cliente.tipo_cliente = tipo_cliente
        cliente.nit = request.POST.get("nit", cliente.nit)
        cliente.nombre_empresa = request.POST.get("nombre_empresa", cliente.nombre_empresa)
        cliente.contacto_alternativo = request.POST.get(
            "contacto_alternativo", cliente.contacto_alternativo
        )
        cliente.observaciones = request.POST.get("observaciones", cliente.observaciones)
        cliente.es_vip = request.POST.get("es_vip") == "on"

        try:
            with transaction.atomic():
                cliente.save()

                telefono = request.POST.get("telefono")
                estado = request.POST.get("estado")

                if telefono:
                    usuario.telefono = telefono
                if estado:
                    usuario.estado = estado
                    usuario.user.is_active = estado == "activo"
                    usuario.user.save()
                cliente.full_clean()
                usuario.full_clean()

                usuario.save()

            messages.success(
                request, f"Datos del cliente {usuario.nombres} actualizados exitosamente."
            )
            return redirect("clientes:detalle_cliente", id=usuario.id)

        except Exception as e:
            messages.error(request, f"Error al guardar: {e}")

    context = {
        "usuario_cliente": usuario,
        "cliente": cliente,
        "tipos_cliente": Cliente.TIPOS_CLIENTE,
    }
    return render(request, "clientes/admin_editar.html", context)
