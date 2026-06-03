import re
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.ordenes.models import DetallePedido, Pedido
from apps.usuarios.models import MaterialConstruccion as Material
from apps.usuarios.models import Stock, Usuario
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


def parse_fecha_entrega(value):
    if not value:
        return None
    value = value.strip()

    # Try ISO formats first.
    for candidate in [value, value.replace(' ', 'T')]:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass

    # Normalize common variations:
    # - allow / or - separators
    # - allow dots between date parts
    # - allow AM/PM in text or compact form
    normalized = value.lower()
    normalized = re.sub(r'[\.]+', '/', normalized)
    normalized = normalized.replace('-', '/')
    normalized = normalized.replace(',', ' ')
    normalized = normalized.replace(' a.m.', ' am').replace(' p.m.', ' pm')
    normalized = normalized.replace(' a.m', ' am').replace(' p.m', ' pm')
    normalized = normalized.replace('am', ' am').replace('pm', ' pm')
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    formats = [
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y %I:%M %p',
        '%d/%m/%Y',
        '%Y/%m/%d %H:%M',
        '%Y/%m/%d %I:%M %p',
        '%Y/%m/%d',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%dT%H:%M',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            if fmt in ('%d/%m/%Y', '%Y/%m/%d'):
                return dt.replace(hour=0, minute=0)
            return dt
        except ValueError:
            continue

    return None


@login_required
def panel_cliente(request):
    try:
        usuario = request.user.usuario
        try:
            cliente, created = Cliente.objects.get_or_create(usuario=usuario)
        except Exception as e_c:
            if "duplicate key" in str(e_c).lower() and conexion_remota_disponible():
                from django.db import connections
                query = (
                    "SELECT setval(pg_get_serial_sequence('cliente', 'id'), "
                    "(SELECT MAX(id) FROM cliente));"
                )
                with connections['remota'].cursor() as cursor:
                    cursor.execute(query)
                cliente, created = Cliente.objects.get_or_create(usuario=usuario)
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

    pedidos = Pedido.objects.filter(usuario=usuario)
    context = {
        "pedidos_activos": pedidos.filter(estado="pendiente").count(),
        "entregas": pedidos.filter(estado="entregado").count(),
        "total_gastado": pedidos.aggregate(total=Sum("total"))["total"] or 0,
        "ultimos_pedidos": (
            pedidos.order_by("-fecha_solicitud")
            .only(
                'codigo_pedido',
                'estado',
                'total',
                'fecha_solicitud',
                'direccion_destino',
                'precio',
            )[:5]
        ),
    }
    return render(request, "clientes/lista.html", context)

@login_required
def mis_pedidos(request):
    try:
        usuario = request.user.usuario
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")

    pedidos = Pedido.objects.filter(
        usuario=usuario
    ).order_by("-fecha_solicitud")
    return render(request, "clientes/mis_pedidos.html", {
        "pedidos": pedidos
    })

@login_required
def perfil_cliente(request):
    try:
        usuario = request.user.usuario
    except (Usuario.DoesNotExist, AttributeError):
        logout(request)
        return redirect("usuarios:login")

    pedidos = Pedido.objects.filter(usuario=usuario)

    context = {
        "cliente": usuario,
        "total_pedidos": pedidos.count(),
        "pedidos_pendientes": pedidos.filter(estado="pendiente").count(),
        "en_ruta": pedidos.filter(estado="en_ruta").count(),
        "total_invertido": pedidos.aggregate(total=Sum("total"))["total"] or 0
    }

    return render(request, "clientes/detalle.html", context)

@login_required
def seguimiento_pedidos(request):
    try:
        usuario = request.user.usuario
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")

    pedidos = Pedido.objects.filter(usuario=usuario).order_by("-fecha_solicitud")
    return render(request, "clientes/seguimiento.html", {
        "pedidos": pedidos
    })

@login_required
def historial_pedidos(request):
    try:
        usuario = request.user.usuario
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")

    pedidos = Pedido.objects.filter(
        usuario=usuario,
        estado="entregado"
    ).order_by("-fecha_solicitud")
    return render(request, "clientes/historial.html", {
        "pedidos": pedidos
    })

@login_required
def crear_pedido(request):
    usuario = request.user.usuario
    if usuario.rol != 'cliente':
        messages.error(request, "Solo los clientes pueden solicitar nuevos pedidos.")
        return redirect("usuarios:panel")

    try:
        cliente, created = Cliente.objects.get_or_create(usuario=usuario)
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")

    materiales = Material.objects.all()

    if request.method == "POST":
        materiales_ids = request.POST.getlist('material_id[]')
        cantidades = request.POST.getlist('cantidad[]')
        ciudad = request.POST.get("ciudad", "").strip()
        direccion_detalle = request.POST.get("direccion_detalle", "").strip()
        direccion = construir_direccion_destino(ciudad, direccion_detalle)
        fecha_entrega_raw = request.POST.get("fecha_entrega")
        fecha_entrega = parse_fecha_entrega(fecha_entrega_raw)

        if fecha_entrega_raw and not fecha_entrega:
            messages.error(request, "Formato de fecha inválido. Usa DD/MM/YYYY HH:MM, DD-MM-YYYY HH:MM o 2026-12-31 15:30.")
            return render(request, "clientes/form.html", _contexto_formulario_pedido(
                materiales=materiales,
                action="crear",
                fecha_entrega=fecha_entrega_raw,
                ciudad=ciudad,
                direccion_detalle=direccion_detalle,
            ))

        if not materiales_ids or not ciudad or not direccion_detalle:
            messages.error(request, "Agrega materiales, selecciona la ciudad de destino e indica la dirección.")
            return render(request, "clientes/form.html", _contexto_formulario_pedido(
                materiales=materiales,
                action="crear",
                fecha_entrega=fecha_entrega_raw,
                ciudad=ciudad,
                direccion_detalle=direccion_detalle,
            ))

        if not ciudad_valida(ciudad):
            messages.error(request, "La ciudad seleccionada no está dentro de la zona de despacho autorizada.")
            return render(request, "clientes/form.html", _contexto_formulario_pedido(
                materiales=materiales,
                action="crear",
                fecha_entrega=fecha_entrega_raw,
                ciudad=ciudad,
                direccion_detalle=direccion_detalle,
            ))

        if len(materiales_ids) != len(cantidades):
            messages.error(request, "Error en los datos del formulario. Intenta nuevamente.")
            return render(request, "clientes/form.html", _contexto_formulario_pedido(
                materiales=materiales,
                action="crear",
                fecha_entrega=fecha_entrega_raw,
                ciudad=ciudad,
                direccion_detalle=direccion_detalle,
            ))

        try:
            with transaction.atomic():
                total_general = 0
                nuevo_pedido = Pedido.objects.create(
                    usuario=usuario,
                    direccion_origen="Bodega Central",
                    direccion_destino=direccion,
                    estado="pendiente",
                    fecha_entrega_programada=fecha_entrega if fecha_entrega else None
                )

                for m_id, cant in zip(materiales_ids, cantidades, strict=False):
                    if not m_id or not cant:
                        continue

                    material = get_object_or_404(Material, pk=m_id)
                    try:
                        stock_obj = Stock.objects.select_for_update().get(material=material)
                    except Stock.DoesNotExist:
                        stock_obj = Stock.objects.create(material=material, cantidad_actual=0)

                    try:
                        cantidad = int(cant)
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

                    DetallePedido.objects.create(
                        pedido=nuevo_pedido,
                        material=material,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario
                    )

                    stock_obj.cantidad_actual = F('cantidad_actual') - cantidad
                    stock_obj.save()

                nuevo_pedido.total = total_general
                nuevo_pedido.save()

            messages.success(request, f"Pedido #{nuevo_pedido.codigo_pedido} creado correctamente.")
            return redirect("clientes:mis_pedidos")

        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "clientes/form.html", _contexto_formulario_pedido(
                materiales=materiales,
                action="crear",
            ))
        except Exception as e:
            messages.error(request, f"Error interno: {e}")
            return render(request, "clientes/form.html", _contexto_formulario_pedido(
                materiales=materiales,
                action="crear",
            ))

    return render(request, "clientes/form.html", _contexto_formulario_pedido(
        materiales=materiales,
        action="crear",
    ))

@login_required
def editar_pedido(request, id):
    pedido = get_object_or_404(Pedido, codigo_pedido=id)
    materiales = Material.objects.all()

    es_admin = request.user.usuario.rol == 'admin'
    es_dueno = request.user.usuario == pedido.usuario

    if not (es_admin or es_dueno) or pedido.estado != 'pendiente':
        messages.error(
            request,
            "No tienes permiso para editar este pedido o el pedido ya no se puede modificar."
        )
        if es_admin:
            return redirect("ordenes:lista_pedidos_admin")
        return redirect("clientes:mis_pedidos")

    if request.method == "POST":
        materiales_ids = request.POST.getlist('material_id[]')
        cantidades = request.POST.getlist('cantidad[]')
        ciudad = request.POST.get("ciudad", "").strip()
        direccion_detalle = request.POST.get("direccion_detalle", "").strip()
        direccion = construir_direccion_destino(ciudad, direccion_detalle)
        fecha_entrega_raw = request.POST.get("fecha_entrega")
        fecha_entrega = parse_fecha_entrega(fecha_entrega_raw)

        if fecha_entrega_raw and not fecha_entrega:
            messages.error(request, "Formato de fecha inválido. Usa DD/MM/YYYY HH:MM, DD-MM-YYYY HH:MM o 2026-12-31 15:30.")
            return render(request, "clientes/form.html", _contexto_formulario_pedido(
                orden=pedido,
                materiales=materiales,
                action="editar",
                fecha_entrega=fecha_entrega_raw,
                ciudad=ciudad,
                direccion_detalle=direccion_detalle,
            ))

        if not materiales_ids or not ciudad or not direccion_detalle:
            messages.error(request, "Datos incompletos: materiales, ciudad y dirección son obligatorios.")
            return render(request, "clientes/form.html", _contexto_formulario_pedido(
                orden=pedido,
                materiales=materiales,
                action="editar",
                fecha_entrega=fecha_entrega_raw,
                ciudad=ciudad,
                direccion_detalle=direccion_detalle,
            ))

        if not ciudad_valida(ciudad):
            messages.error(request, "La ciudad seleccionada no está dentro de la zona de despacho autorizada.")
            return render(request, "clientes/form.html", _contexto_formulario_pedido(
                orden=pedido,
                materiales=materiales,
                action="editar",
                fecha_entrega=fecha_entrega_raw,
                ciudad=ciudad,
                direccion_detalle=direccion_detalle,
            ))

        try:
            with transaction.atomic():
                for detalle in pedido.detalles.all():
                    try:
                        stock_obj = Stock.objects.select_for_update().get(material=detalle.material)
                    except Stock.DoesNotExist:
                        stock_obj = Stock.objects.create(
                            material=detalle.material,
                            cantidad_actual=0,
                        )
                    stock_obj.cantidad_actual = F('cantidad_actual') + detalle.cantidad
                    stock_obj.save()

                pedido.detalles.all().delete()

                total_general = 0
                for m_id, cant in zip(materiales_ids, cantidades, strict=False):
                    material = get_object_or_404(Material, pk=m_id)
                    try:
                        stock_obj = Stock.objects.select_for_update().get(material=material)
                    except Stock.DoesNotExist:
                        stock_obj = Stock.objects.create(material=material, cantidad_actual=0)
                    cantidad = int(cant)

                    if stock_obj.cantidad_actual < cantidad:
                        raise ValueError(f"Stock insuficiente para {material.nombre}")

                    DetallePedido.objects.create(
                        pedido=pedido,
                        material=material,
                        cantidad=cantidad,
                        precio_unitario=material.precio
                    )

                    stock_obj.cantidad_actual = F('cantidad_actual') - cantidad
                    stock_obj.save()
                    total_general += material.precio * cantidad

                pedido.direccion_destino = direccion
                pedido.fecha_entrega_programada = fecha_entrega if fecha_entrega else None
                pedido.total = total_general
                pedido.save()

            messages.success(request, f"Pedido #{pedido.codigo_pedido} actualizado correctamente.")
            if es_admin:
                return redirect("ordenes:lista_pedidos_admin")
            return redirect("clientes:mis_pedidos")

        except Exception as e:
            messages.error(request, f"Error al actualizar el pedido: {e}")

    ciudad_ini, detalle_ini = separar_direccion_destino(pedido.direccion_destino)
    return render(request, "clientes/form.html", _contexto_formulario_pedido(
        orden=pedido,
        materiales=materiales,
        action="editar",
        ciudad=ciudad_ini,
        direccion_detalle=detalle_ini,
    ))

@login_required
def cancelar_pedido(request, id):
    pedido = get_object_or_404(Pedido, codigo_pedido=id)

    es_admin = request.user.usuario.rol == 'admin'
    es_dueno = request.user.usuario == pedido.usuario

    if not (es_admin or es_dueno):
        messages.error(request, "No tienes permiso para cancelar este pedido.")
        if es_admin:
            return redirect("ordenes:lista_pedidos_admin")
        return redirect("clientes:mis_pedidos")

    if pedido.estado != 'pendiente':
        messages.error(request, "Solo se pueden cancelar pedidos en estado pendiente.")
        if es_admin:
            return redirect("ordenes:lista_pedidos_admin")
        return redirect("clientes:mis_pedidos")

    try:
        with transaction.atomic():
            for detalle in pedido.detalles.all():
                try:
                    stock_obj = Stock.objects.select_for_update().get(material=detalle.material)
                except Stock.DoesNotExist:
                    stock_obj = Stock.objects.create(material=detalle.material, cantidad_actual=0)
                stock_obj.cantidad_actual = F('cantidad_actual') + detalle.cantidad
                stock_obj.save()

            pedido.estado = "cancelado"
            pedido.save()

            from apps.historial.utils import registrar_actividad
            comentario = (
                f"Pedido #{pedido.codigo_pedido} cancelado por "
                f"{'admin' if es_admin else 'cliente'}"
            )
            registrar_actividad(
                request,
                'cancelar_pedido',
                'pedidos',
                pedido.codigo_pedido,
                comentario,
            )

        messages.warning(
            request,
            f"Pedido #{pedido.codigo_pedido} ha sido cancelado y el stock ha sido devuelto."
        )
    except Exception as e:
        messages.error(request, f"Error al cancelar el pedido: {e}")

    if es_admin:
        return redirect("ordenes:lista_pedidos_admin")
    return redirect("clientes:mis_pedidos")
