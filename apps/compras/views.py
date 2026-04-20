from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Proveedor, Compra, DetalleCompra
from django.contrib import messages
from historial.utils import registrar_actividad

@login_required
def lista_proveedores(request):
    proveedores = Proveedor.objects.all()
    return render(request, "compras/proveedores_lista.html", {"proveedores": proveedores})

@login_required
def crear_proveedor(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        nit = request.POST.get("nit")
        contacto = request.POST.get("contacto")
        telefono = request.POST.get("telefono")
        email = request.POST.get("email")
        direccion = request.POST.get("direccion")
        
        Proveedor.objects.create(
            nombre=nombre,
            nit=nit,
            contacto=contacto,
            telefono=telefono,
            email=email,
            direccion=direccion
        )
        registrar_actividad(request, 'crear', 'proveedores', nit, f"Proveedor creado: {nombre}")
        messages.success(request, "Proveedor registrado con éxito.")
        return redirect("compras:lista_proveedores")
        
    return render(request, "compras/proveedor_form.html", {"action": "Crear"})

@login_required
def editar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    if request.method == "POST":
        proveedor.nombre = request.POST.get("nombre")
        proveedor.nit = request.POST.get("nit")
        proveedor.contacto = request.POST.get("contacto")
        proveedor.telefono = request.POST.get("telefono")
        proveedor.email = request.POST.get("email")
        proveedor.direccion = request.POST.get("direccion")
        proveedor.save()
        
        registrar_actividad(request, 'editar', 'proveedores', proveedor.nit, f"Proveedor editado: {proveedor.nombre}")
        messages.success(request, "Proveedor actualizado.")
        return redirect("compras:lista_proveedores")
        
    return render(request, "compras/proveedor_form.html", {"proveedor": proveedor, "action": "Editar"})

# ── HU-23 ──────────────────────────────────────────────────────────────────
import json
from .models import OrdenCompra, ItemOrdenCompra

@login_required
def registrar_orden_compra(request):
    proveedores = Proveedor.objects.filter(estado=True)

    if request.method == 'POST':
        proveedor_id  = request.POST.get('proveedor_id')
        observaciones = request.POST.get('observaciones', '')
        materiales    = json.loads(request.POST.get('materiales_json', '[]'))

        if not proveedor_id:
            messages.error(request, 'Selecciona un proveedor activo.')
            return redirect('compras:registrar_orden')

        if not materiales:
            messages.error(request, 'Agrega al menos un material.')
            return redirect('compras:registrar_orden')

        proveedor = get_object_or_404(Proveedor, pk=proveedor_id, estado=True)

        orden = OrdenCompra.objects.create(
            proveedor=proveedor,
            observaciones=observaciones,
        )

        for m in materiales:
            ItemOrdenCompra.objects.create(
                orden=orden,
                nombre_material=m['nombre'],
                cantidad=m['cantidad'],
                precio_unitario=m['precio'],
            )

        orden.calcular_total()

        registrar_actividad(
            request, 'crear', 'compras', orden.numero_orden,
            f'Orden de compra creada: {orden.numero_orden}'
        )

        messages.success(request, f'Orden {orden.numero_orden} guardada como pendiente.')
        return redirect('compras:detalle_orden', pk=orden.pk)

    return render(request, 'compras/registrar_orden.html', {'proveedores': proveedores})


@login_required
def detalle_orden_compra(request, pk):
    orden = get_object_or_404(OrdenCompra.objects.prefetch_related('items'), pk=pk)
    return render(request, 'compras/detalle_orden.html', {'orden': orden})


@login_required
def lista_ordenes_compra(request):
    ordenes = OrdenCompra.objects.select_related('proveedor').all()
    return render(request, 'compras/lista_ordenes.html', {'ordenes': ordenes})


@login_required
def editar_orden_compra(request, pk):
    orden = get_object_or_404(OrdenCompra, pk=pk)
    proveedores = Proveedor.objects.filter(estado=True)

    if request.method == 'POST':
        orden.proveedor_id = request.POST.get('proveedor_id')
        orden.observaciones = request.POST.get('observaciones', '')
        orden.save()

        registrar_actividad(
            request, 'editar', 'compras', orden.numero_orden,
            f'Orden editada: {orden.numero_orden}'
        )

        messages.success(request, 'Orden actualizada correctamente.')
        return redirect('compras:detalle_orden', pk=orden.pk)

    return render(request, 'compras/editar_orden.html', {
        'orden': orden,
        'proveedores': proveedores
    })


# 🔥 NUEVA FUNCIÓN (CAMBIAR ESTADO)
@login_required
def cambiar_estado_orden(request, pk, estado):
    orden = get_object_or_404(OrdenCompra, pk=pk)

    estados_validos = ['pendiente', 'aprobada', 'cancelada']

    if estado not in estados_validos:
        messages.error(request, 'Estado inválido.')
        return redirect('compras:detalle_orden', pk=pk)

    orden.estado = estado
    orden.save()

    registrar_actividad(
        request,
        'editar',
        'compras',
        orden.numero_orden,
        f'Estado cambiado a {estado}'
    )

    messages.success(request, f'Estado actualizado a {estado}.')
    return redirect('compras:detalle_orden', pk=pk)