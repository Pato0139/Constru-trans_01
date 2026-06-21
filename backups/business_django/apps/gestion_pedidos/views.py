from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.usuarios.models import MaterialConstruccion, Stock
from apps.usuarios.views import admin_required

from .models import DetallePedido, Pedido


@login_required
@transaction.atomic
def crear_pedido(request):
    """
    Vista para crear un pedido.
    Recibe una lista de materiales y cantidades vía POST.
    Valida el stock antes de proceder.
    """
    materiales = MaterialConstruccion.objects.all()

    if request.method == "POST":
        materiales_ids = request.POST.getlist("materiales[]")
        cantidades = request.POST.getlist("cantidades[]")
        descuento = request.POST.get("descuento", 0)

        if not materiales_ids:
            messages.error(request, "Debe agregar al menos un material al pedido.")
            context = {"materiales": materiales}

            return render(request, "gestion_pedidos/crear_pedido.html", context)

        try:
            pedido = Pedido.objects.create(
                cliente=request.user, descuento=descuento, estado="pendiente"
            )

            for m_id, cant in zip(materiales_ids, cantidades, strict=False):
                cant = int(cant)
                material = get_object_or_404(MaterialConstruccion, pk=m_id)
                stock_obj = Stock.objects.select_for_update().get(material=material)

                if stock_obj.cantidad_actual < cant:
                    # Si falla un material, lanzamos excepción para que el atomic haga rollback
                    raise ValueError(
                        f"Stock insuficiente para {material.nombre}. Disponible: {stock_obj.cantidad_actual}"
                    )

                stock_obj.cantidad_actual -= cant
                stock_obj.save()

                DetallePedido.objects.create(pedido=pedido, material=material, cantidad=cant)

            messages.success(request, f"Pedido #{pedido.id} creado exitosamente.")
            return redirect("gestion_pedidos:lista")

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error al procesar el pedido: {str(e)}")

    context = {"materiales": materiales}

    return render(request, "gestion_pedidos/crear_pedido.html", context)


@login_required
def listar_pedidos(request):
    """
    Lista de pedidos filtrada por rol.
    Admin ve todos, Cliente ve los suyos.
    """
    if request.user.rol == "admin":
        pedidos = Pedido.objects.all()
    else:
        pedidos = Pedido.objects.filter(cliente=request.user)

    context = {"pedidos": pedidos}

    return render(request, "gestion_pedidos/listar_pedidos.html", context)


@login_required
def detalle_pedido(request, pk):
    """
    Detalle de un pedido específico.
    """
    pedido = get_object_or_404(Pedido, pk=pk)

    # Seguridad básica
    if request.user.rol != "admin" and pedido.cliente != request.user:
        messages.error(request, "No tiene permisos para ver este pedido.")
        return redirect("gestion_pedidos:lista")

    context = {"pedido": pedido}

    return render(request, "gestion_pedidos/detalle_pedido.html", context)


@admin_required
@transaction.atomic
def aprobar_pedido(request, pk):
    """
    Cambia el estado del pedido a aprobado. Solo Administradores.
    """
    pedido = get_object_or_404(Pedido, pk=pk)
    if pedido.estado == "pendiente":
        pedido.estado = "aprobado"
        pedido.save()
        messages.success(request, f"Pedido #{pedido.id} aprobado.")
    else:
        messages.warning(request, "Solo se pueden aprobar pedidos en estado pendiente.")

    return redirect("gestion_pedidos:detalle", pk=pk)


@admin_required
@transaction.atomic
def cancelar_pedido(request, pk):
    """
    Cancela un pedido y devuelve el stock. Solo Administradores.
    """
    pedido = get_object_or_404(Pedido, pk=pk)
    if pedido.estado not in ["cancelado", "entregado"]:
        # Devolver stock
        for detalle in pedido.detalles.all():
            stock_obj = Stock.objects.select_for_update().get(material=detalle.material)
            stock_obj.cantidad_actual += detalle.cantidad
            stock_obj.save()

        pedido.estado = "cancelado"
        pedido.save()
        messages.success(request, f"Pedido #{pedido.id} cancelado y stock devuelto.")
    else:
        messages.warning(request, "Este pedido no puede ser cancelado.")

    return redirect("gestion_pedidos:detalle", pk=pk)
