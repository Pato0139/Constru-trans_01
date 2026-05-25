from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.ordenes.models import DetallePedido, Pedido
from apps.usuarios.models import MaterialConstruccion as Material
from apps.usuarios.models import Stock, Usuario
from core.utils import conexion_remota_disponible

from .models import Cliente

@login_required
def panel_cliente(request):
    try:
        usuario = request.user.usuario
        try:
            cliente, created = Cliente.objects.get_or_create(usuario=usuario)
        except Exception as e_c:
            if "duplicate key" in str(e_c).lower() and conexion_remota_disponible():
                from django.db import connections
                with connections['remota'].cursor() as cursor:
                    cursor.execute("SELECT setval(pg_get_serial_sequence('cliente', 'id'), (SELECT MAX(id) FROM cliente));")
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
        "entregadas": pedidos.filter(estado="entregado").count(),
        "total_gastado": pedidos.aggregate(total=Sum("total"))["total"] or 0,
        "ultimos_pedidos": pedidos.order_by("-fecha_solicitud").only('id', 'codigo_pedido', 'estado', 'total', 'fecha_solicitud', 'direccion_destino')[:5]
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
        direccion = request.POST.get("direccion")
        fecha_entrega = request.POST.get("fecha_entrega")

        if not materiales_ids or not direccion:
            messages.error(request, "Por favor, agrega al menos un material y la dirección.")
            return render(request, "clientes/form.html", {
                "materiales": materiales,
                "action": "crear"
            })

        if len(materiales_ids) != len(cantidades):
            messages.error(request, "Error en los datos del formulario. Intenta nuevamente.")
            return render(request, "clientes/form.html", {
                "materiales": materiales,
                "action": "crear"
            })

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

                    material = get_object_or_404(Material, id=m_id)
                    try:
                        stock_obj = Stock.objects.select_for_update().get(material=material)
                    except Stock.DoesNotExist:
                        stock_obj = Stock.objects.create(material=material, cantidad_actual=0)

                    try:
                        cantidad = int(cant)
                    except (ValueError, TypeError):
                        raise ValueError(f"Cantidad inválida para {material.nombre}")

                    if cantidad <= 0:
                        raise ValueError(f"La cantidad para {material.nombre} debe ser mayor a 0.")

                    if stock_obj.cantidad_actual < cantidad:
                        raise ValueError(f"Stock insuficiente para {material.nombre}. Quedan {stock_obj.cantidad_actual}.")

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
            return render(request, "clientes/form.html", {
                "materiales": materiales,
                "action": "crear"
            })
        except Exception as e:
            messages.error(request, f"Error interno: {e}")
            return render(request, "clientes/form.html", {
                "materiales": materiales,
                "action": "crear"
            })

    return render(request, "clientes/form.html", {
        "materiales": materiales,
        "action": "crear"
    })

@login_required
def editar_pedido(request, id):
    pedido = get_object_or_404(Pedido, codigo_pedido=id)
    materiales = Material.objects.all()

    es_admin = request.user.usuario.rol == 'admin'
    es_dueno = request.user.usuario == pedido.usuario

    if not (es_admin or es_dueno) or pedido.estado != 'pendiente':
        messages.error(request, "No tienes permiso para editar este pedido o el pedido ya no se puede modificar.")
        if es_admin:
            return redirect("ordenes:lista_pedidos_admin")
        return redirect("clientes:mis_pedidos")

    if request.method == "POST":
        materiales_ids = request.POST.getlist('material_id[]')
        cantidades = request.POST.getlist('cantidad[]')
        direccion = request.POST.get("direccion")
        fecha_entrega = request.POST.get("fecha_entrega")
        # Variable no utilizada actualmente (reservada para implementación futura)
        # metodo_pago = request.POST.get("metodo_pago", "efectivo")

        if not materiales_ids or not direccion:
            messages.error(request, "Datos incompletos.")
            return render(request, "clientes/form.html", {
                "orden": pedido,
                "materiales": materiales,
                "action": "editar"
            })

        try:
            with transaction.atomic():
                for detalle in pedido.detalles.all():
                    try:
                        stock_obj = Stock.objects.select_for_update().get(material=detalle.material)
                    except Stock.DoesNotExist:
                        stock_obj = Stock.objects.create(material=detalle.material, cantidad_actual=0)
                    stock_obj.cantidad_actual = F('cantidad_actual') + detalle.cantidad
                    stock_obj.save()

                pedido.detalles.all().delete()

                total_general = 0
                for m_id, cant in zip(materiales_ids, cantidades, strict=False):
                    material = get_object_or_404(Material, id=m_id)
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

    return render(request, "clientes/form.html", {
        "orden": pedido,
        "materiales": materiales,
        "action": "editar"
    })

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
            registrar_actividad(request, 'cancelar_pedido', 'pedidos', pedido.codigo_pedido, f"Pedido #{pedido.codigo_pedido} cancelado por {'admin' if es_admin else 'cliente'}")

        messages.warning(request, f"Pedido #{pedido.codigo_pedido} ha sido cancelado y el stock ha sido devuelto.")
    except Exception as e:
        messages.error(request, f"Error al cancelar el pedido: {e}")

    if es_admin:
        return redirect("ordenes:lista_pedidos_admin")
    return redirect("clientes:mis_pedidos")
