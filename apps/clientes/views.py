from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db.models import Sum, F
from django.contrib import messages
from apps.ordenes.models import Orden, DetalleOrden
from apps.usuarios.models import Material, Usuario, Stock
from django.db import transaction

@login_required
def panel_cliente(request):
    try:
        usuario = request.user.usuario
        cliente = usuario.perfil_cliente
    except (Usuario.DoesNotExist, AttributeError):
        logout(request)
        return redirect("usuarios:login")
        
    pedidos = Orden.objects.filter(cliente=cliente)
    context = {
        "pedidos_activos": pedidos.filter(estado="pendiente").count(),
        "entregadas": pedidos.filter(estado="entregado").count(),
        "total_gastado": pedidos.aggregate(total=Sum("precio"))["total"] or 0,
        "ultimos_pedidos": pedidos.order_by("-fecha")[:5]
    }
    return render(request, "clientes/lista.html", context)

@login_required
def mis_pedidos(request):
    try:
        cliente = request.user.usuario.perfil_cliente
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")
        
    pedidos = Orden.objects.filter(
        cliente=cliente
    ).order_by("-fecha")
    return render(request, "clientes/mis_pedidos.html", {
        "pedidos": pedidos
    })

@login_required
def perfil_cliente(request):
    try:
        usuario = request.user.usuario
        cliente_perfil = usuario.perfil_cliente
    except (Usuario.DoesNotExist, AttributeError):
        logout(request)
        return redirect("usuarios:login")
        
    pedidos = Orden.objects.filter(cliente=cliente_perfil)
    
    context = {
        "cliente": usuario,
        "total_pedidos": pedidos.count(),
        "pedidos_pendientes": pedidos.filter(estado="pendiente").count(),
        "en_ruta": pedidos.filter(estado="en_ruta").count(),
        "total_invertido": pedidos.aggregate(total=Sum("precio"))["total"] or 0
    }
    
    return render(request, "clientes/detalle.html", context)

@login_required
def seguimiento_pedidos(request):
    try:
        cliente = request.user.usuario.perfil_cliente
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")
        
    pedidos = Orden.objects.filter(cliente=cliente).order_by("-fecha")
    return render(request, "clientes/seguimiento.html", {
        "pedidos": pedidos
    })

@login_required
def historial_pedidos(request):
    try:
        cliente = request.user.usuario.perfil_cliente
    except AttributeError:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect("usuarios:panel")
        
    pedidos = Orden.objects.filter(
        cliente=cliente, 
        estado="entregado"
    ).order_by("-fecha")
    return render(request, "clientes/historial.html", {
        "pedidos": pedidos
    })

@login_required
def crear_pedido(request):
    # Restricción: Solo clientes pueden solicitar pedidos
    usuario = request.user.usuario
    if usuario.rol != 'cliente':
        messages.error(request, "Solo los clientes pueden solicitar nuevos pedidos.")
        return redirect("usuarios:panel")
        
    try:
        cliente = usuario.perfil_cliente
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

        try:
            total_general = 0

            with transaction.atomic():
                nueva_orden = Orden.objects.create(
                    cliente=cliente,
                    direccion_origen="Bodega Central",
                    direccion_destino=direccion,
                    estado="pendiente",
                    fecha_entrega_programada=fecha_entrega if fecha_entrega else None
                )

                for m_id, cant in zip(materiales_ids, cantidades):
                    # Bloqueamos la fila de stock para evitar sobreventa simultánea
                    material = get_object_or_404(Material, id=m_id)
                    stock_obj = Stock.objects.select_for_update().get(material=material)
                    
                    cantidad = int(cant)

                    if cantidad <= 0:
                        raise ValueError(f"La cantidad para {material.nombre} debe ser mayor a 0.")

                    if stock_obj.cantidad < cantidad:
                        raise ValueError(f"Stock insuficiente para {material.nombre}. Quedan {stock_obj.cantidad}.")

                    precio_unitario = material.precio
                    total_item = precio_unitario * cantidad
                    total_general += total_item

                    DetalleOrden.objects.create(
                        orden=nueva_orden,
                        material=material,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario
                    )
                    
                    # Descontamos stock sobre el objeto Stock
                    stock_obj.cantidad = F('cantidad') - cantidad
                    stock_obj.save()

                    # HU-18: Registrar movimiento de salida
                    from apps.inventario.models import MovimientoInventario
                    MovimientoInventario.objects.create(
                        material=material,
                        tipo='salida',
                        cantidad=cantidad,
                        motivo=f"orden #{nueva_orden.id}",
                        referencia_id=nueva_orden.id,
                        usuario=request.user
                    )

                nueva_orden.precio = total_general
                nueva_orden.save()

            messages.success(request, f"Pedido #{nueva_orden.id} creado correctamente.")
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
    orden = get_object_or_404(Orden, id=id)
    materiales = Material.objects.all()
    
    # Solo el cliente dueño puede editar y solo si está pendiente
    if request.user.usuario != orden.cliente or orden.estado != 'pendiente':
        messages.error(request, "No puedes editar este pedido.")
        return redirect("clientes:mis_pedidos")

    if request.method == "POST":
        materiales_ids = request.POST.getlist('material_id[]')
        cantidades = request.POST.getlist('cantidad[]')
        direccion = request.POST.get("direccion")
        fecha_entrega = request.POST.get("fecha_entrega")

        if not materiales_ids or not direccion:
            messages.error(request, "Datos incompletos.")
            return render(request, "clientes/form.html", {
                "orden": orden,
                "materiales": materiales,
                "action": "editar"
            })

        try:
            with transaction.atomic():
                # Devolver stock de los detalles anteriores
                for detalle in orden.detalles.all():
                    stock_obj = Stock.objects.select_for_update().get(material=detalle.material)
                    stock_obj.cantidad = F('cantidad') + detalle.cantidad
                    stock_obj.save()
                
                # Eliminar detalles antiguos
                orden.detalles.all().delete()

                total_general = 0
                for m_id, cant in zip(materiales_ids, cantidades):
                    material = get_object_or_404(Material, id=m_id)
                    stock_obj = Stock.objects.select_for_update().get(material=material)
                    cantidad = int(cant)

                    if stock_obj.cantidad < cantidad:
                        raise ValueError(f"Stock insuficiente para {material.nombre}")

                    DetalleOrden.objects.create(
                        orden=orden,
                        material=material,
                        cantidad=cantidad,
                        precio_unitario=material.precio
                    )
                    
                    stock_obj.cantidad = F('cantidad') - cantidad
                    stock_obj.save()
                    total_general += material.precio * cantidad

                orden.direccion_destino = direccion
                orden.fecha_entrega_programada = fecha_entrega if fecha_entrega else None
                orden.precio = total_general
                orden.save()

            messages.success(request, f"Pedido #{orden.id} actualizado.")
            return redirect("clientes:mis_pedidos")

        except Exception as e:
            messages.error(request, f"Error: {e}")
            
    return render(request, "clientes/form.html", {
        "orden": orden,
        "materiales": materiales,
        "action": "editar"
    })

@login_required
def eliminar_orden(request, id):
    orden = get_object_or_404(Orden, id=id)
    orden.estado = "cancelado"
    orden.save()
    messages.warning(request, f"Pedido #{orden.id} ha sido cancelado.")
    return redirect("clientes:mis_pedidos")
