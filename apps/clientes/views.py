import re
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.facturacion.models import Factura
from apps.ordenes.models import DetallePedido, Pedido
from apps.pagos.models import Pago
from apps.usuarios.models import Catalogo, MetodoPago, Stock, UnidadMedida, Usuario
from apps.usuarios.models import MaterialConstruccion as Material
from core.db_preference import debe_usar_bd_remota
from core.despacho import (
    CIUDADES_DESPACHO,
    ciudad_valida,
    construir_direccion_destino,
    separar_direccion_destino,
)
from core.utils import conexion_remota_disponible

from .models import Cliente


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


def _obtener_cliente_local(usuario_local):
    cliente_local, _ = Cliente.objects.get_or_create(
        usuario=usuario_local,
        defaults={"direccion": "Por definir"},
    )
    return cliente_local


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
                return dt.replace(hour=0, minute=0)
            return dt
        except ValueError:
            continue

    return None


@login_required
def panel_cliente(request):
    try:
        usuario_remoto = request.user.usuario
        usuario = _obtener_usuario_local(usuario_remoto)
        try:
            cliente, created = Cliente.objects.get_or_create(usuario=usuario_remoto)
        except Exception as e_c:
            if "duplicate key" in str(e_c).lower() and conexion_remota_disponible():
                from django.db import connections

                query = (
                    "SELECT setval(pg_get_serial_sequence('cliente', 'id'), "
                    "(SELECT MAX(id) FROM cliente));"
                )
                with connections["remota"].cursor() as cursor:
                    cursor.execute(query)
                cliente, created = Cliente.objects.get_or_create(usuario=usuario_remoto)
            else:
                raise e_c
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
    pagos = Pago.objects.filter(factura__cliente__in=[usuario, usuario_remoto])
    context = {
        "pedidos_activos": pedidos.filter(estado="pendiente").count(),
        "entregas": pedidos.filter(estado="entregado").count(),
        "total_gastado": pedidos.aggregate(total=Sum("total"))["total"] or 0,
        "total_pagos": pagos.count(),
        "ultimos_pedidos": (
            pedidos.only(
                "codigo_pedido",
                "estado",
                "total",
                "fecha_solicitud",
                "direccion_destino",
                "precio",
            )[:5]
        ),
    }
    return render(request, "clientes/lista.html", context)


@login_required
def mis_pedidos(request):
    try:
        usuario_remoto = request.user.usuario
        usuario = _obtener_usuario_local(usuario_remoto)
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")

    pedidos = pedidos_visibles_para_cliente(usuario, usuario_remoto).select_related("factura").prefetch_related("factura__pagos")
    metodos_pago = MetodoPago.objects.all()
    context = {"pedidos": pedidos, "metodos_pago": metodos_pago}

    return render(request, "clientes/mis_pedidos.html", context)


@login_required
def perfil_cliente(request):
    try:
        usuario_remoto = request.user.usuario
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


@login_required
def seguimiento_pedidos(request):
    try:
        usuario_remoto = request.user.usuario
        usuario = _obtener_usuario_local(usuario_remoto)
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")

    pedidos = pedidos_visibles_para_cliente(usuario, usuario_remoto)
    context = {"pedidos": pedidos}

    return render(request, "clientes/seguimiento.html", context)


@login_required
def historial_pedidos(request):
    try:
        usuario_remoto = request.user.usuario
        usuario = _obtener_usuario_local(usuario_remoto)
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")

    pedidos = pedidos_visibles_para_cliente(usuario, usuario_remoto).filter(estado="entregado")
    context = {"pedidos": pedidos}

    return render(request, "clientes/historial.html", context)


@login_required
def crear_pedido(request):
    usuario_remoto = request.user.usuario
    usuario_local = _obtener_usuario_local(usuario_remoto)
    if usuario_remoto.rol != "cliente":
        messages.error(request, "Solo los clientes pueden solicitar nuevos pedidos.")
        return redirect("usuarios:panel")

    cliente_local = _obtener_cliente_local(usuario_local)
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

        if len(materiales_ids) != len(cantidades):
            messages.error(request, "Error en los datos del formulario. Intenta nuevamente.")
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
        try:
            with transaction.atomic():
                total_general = 0
                nuevo_pedido = Pedido.objects.create(
                    usuario=usuario_local,
                    cliente=cliente_local,
                    direccion_origen="Bodega Central",
                    direccion_destino=direccion,
                    estado="pendiente",
                    fecha_entrega_programada=fecha_entrega if fecha_entrega else None,
                )

                with transaction.atomic(using=db_alias):
                    for m_id, cant in zip(materiales_ids, cantidades, strict=False):
                        if not m_id or not cant:
                            continue

                        material = _obtener_material_local(m_id)
                        try:
                            stock_obj = (
                                Stock.objects.select_for_update()
                                .using(db_alias)
                                .get(material=material)
                            )
                        except Stock.DoesNotExist:
                            stock_obj = Stock.objects.using(db_alias).create(
                                material=material, cantidad_actual=0
                            )

                        try:
                            cantidad = int(cant)
                        except (ValueError, TypeError) as err:
                            raise ValueError(f"Cantidad inválida para {material.nombre}") from err

                        if cantidad <= 0:
                            raise ValueError(
                                f"La cantidad para {material.nombre} debe ser mayor a 0."
                            )

                        if stock_obj.cantidad_actual < cantidad:
                            raise ValueError(
                                f"Stock insuficiente para {material.nombre}. "
                                f"Quedan {stock_obj.cantidad_actual}."
                            )

                        precio_unitario = material.precio
                        total_item = precio_unitario * cantidad
                        total_general += total_item

                        DetallePedido.objects.using("default").create(
                            pedido=nuevo_pedido,
                            material=material,
                            cantidad=cantidad,
                            precio_unitario=precio_unitario,
                        )

                        stock_obj.cantidad_actual = F("cantidad_actual") - cantidad
                        stock_obj.save(using=db_alias)

            messages.success(request, f"Pedido #{nuevo_pedido.codigo_pedido} creado correctamente.")
            return redirect("clientes:mis_pedidos")

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
        except Exception as e:
            messages.error(request, f"Error interno: {e}")
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


@login_required
def editar_pedido(request, id):
    usuario_remoto = request.user.usuario
    pedido = get_object_or_404(Pedido, codigo_pedido=id)
    materiales = Material.objects.all()

    es_admin = usuario_remoto.rol == "admin"
    usuario = _obtener_usuario_local(usuario_remoto)
    es_dueno = _es_dueno_pedido(pedido, usuario_remoto, usuario)

    if not (es_admin or es_dueno) or pedido.estado != "pendiente":
        messages.error(
            request,
            "No tienes permiso para editar este pedido o el pedido ya no se puede modificar.",
        )
        if es_admin:
            return redirect("ordenes:lista_pedidos_admin")
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

        db_alias = _obtener_alias_db()
        try:
            with transaction.atomic():
                with transaction.atomic(using=db_alias):
                    for detalle in pedido.detalles.all():
                        try:
                            stock_obj = (
                                Stock.objects.select_for_update()
                                .using(db_alias)
                                .get(material=detalle.material)
                            )
                        except Stock.DoesNotExist:
                            stock_obj = Stock.objects.using(db_alias).create(
                                material=detalle.material,
                                cantidad_actual=0,
                            )
                        stock_obj.cantidad_actual = F("cantidad_actual") + detalle.cantidad
                        stock_obj.save(using=db_alias)

                    pedido.detalles.all().delete()

                    total_general = 0
                    for m_id, cant in zip(materiales_ids, cantidades, strict=False):
                        material = _obtener_material_local(m_id)
                        try:
                            stock_obj = (
                                Stock.objects.select_for_update()
                                .using(db_alias)
                                .get(material=material)
                            )
                        except Stock.DoesNotExist:
                            stock_obj = Stock.objects.using(db_alias).create(
                                material=material, cantidad_actual=0
                            )
                        cantidad = int(cant)

                        if stock_obj.cantidad_actual < cantidad:
                            raise ValueError(f"Stock insuficiente para {material.nombre}")

                        DetallePedido.objects.using("default").create(
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
                pedido.total = total_general
                pedido.precio = total_general
                pedido.save()

            messages.success(request, f"Pedido #{pedido.codigo_pedido} actualizado correctamente.")
            if es_admin:
                return redirect("ordenes:lista_pedidos_admin")
            return redirect("clientes:mis_pedidos")

        except Exception as e:
            messages.error(request, f"Error al actualizar el pedido: {e}")

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


@login_required
def cancelar_pedido(request, id):
    pedido = get_object_or_404(Pedido, codigo_pedido=id)

    usuario_remoto = request.user.usuario
    es_admin = usuario_remoto.rol == "admin"
    usuario = _obtener_usuario_local(usuario_remoto)
    es_dueno = _es_dueno_pedido(pedido, usuario_remoto, usuario)

    if not (es_admin or es_dueno):
        messages.error(request, "No tienes permiso para cancelar este pedido.")
        if es_admin:
            return redirect("ordenes:lista_pedidos_admin")
        return redirect("clientes:mis_pedidos")

    if pedido.estado != "pendiente":
        messages.error(request, "Solo se pueden cancelar pedidos en estado pendiente.")
        if es_admin:
            return redirect("ordenes:lista_pedidos_admin")
        return redirect("clientes:mis_pedidos")

    db_alias = _obtener_alias_db()
    try:
        with transaction.atomic(using=db_alias):
            for detalle in pedido.detalles.all():
                try:
                    stock_obj = (
                        Stock.objects.select_for_update()
                        .using(db_alias)
                        .get(material=detalle.material)
                    )
                except Stock.DoesNotExist:
                    stock_obj = Stock.objects.using(db_alias).create(
                        material=detalle.material, cantidad_actual=0
                    )
                stock_obj.cantidad_actual = F("cantidad_actual") + detalle.cantidad
                stock_obj.save(using=db_alias)

            pedido.estado = "cancelado"
            pedido.save()

            from apps.historial.utils import registrar_actividad

            comentario = (
                f"Pedido #{pedido.codigo_pedido} cancelado por "
                f"{'admin' if es_admin else 'cliente'}"
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
    except Exception as e:
        messages.error(request, f"Error al cancelar el pedido: {e}")

    if es_admin:
        return redirect("ordenes:lista_pedidos_admin")
    return redirect("clientes:mis_pedidos")


@login_required
def mis_pagos(request):
    try:
        usuario_remoto = request.user.usuario
        usuario = _obtener_usuario_local(usuario_remoto)
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")

    # Facturas pendientes (para pagar)
    facturas_pendientes = (
        Factura.objects.filter(cliente__in=[usuario, usuario_remoto], estado="pendiente")
        .select_related("pedido")
        .prefetch_related("pagos")
    )

    # Historial de pagos
    pagos = (
        Pago.objects.filter(factura__cliente__in=[usuario, usuario_remoto])
        .select_related("factura", "factura__pedido", "codigo_metodo_pago")
        .order_by("-fecha")
    )

    # Métodos de pago disponibles
    metodos_pago = MetodoPago.objects.all()

    context = {
        "facturas_pendientes": facturas_pendientes,
        "pagos": pagos,
        "metodos_pago": metodos_pago,
    }

    return render(request, "clientes/mis_pagos.html", context)
