from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Proveedor, Compra, DetalleCompra
from django.contrib import messages
from historial.utils import registrar_actividad

from apps.usuarios.models import Usuario

@login_required
def lista_proveedores(request):
    try:
        usuario = request.user.usuario
    except Usuario.DoesNotExist:
        from django.contrib.auth import logout
        logout(request)
        return redirect("usuarios:login")

    if usuario.rol != 'admin':
        messages.error(request, "No tienes permisos para ver esta sección.")
        return redirect("usuarios:panel")

    proveedores = Proveedor.objects.all()
    return render(request, "compras/proveedores_lista.html", {"proveedores": proveedores})

@login_required
def crear_proveedor(request):
    try:
        usuario = request.user.usuario
    except Usuario.DoesNotExist:
        from django.contrib.auth import logout
        logout(request)
        return redirect("usuarios:login")

    if usuario.rol != 'admin':
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("usuarios:panel")

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
    try:
        usuario = request.user.usuario
    except Usuario.DoesNotExist:
        from django.contrib.auth import logout
        logout(request)
        return redirect("usuarios:login")

    if usuario.rol != 'admin':
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("usuarios:panel")

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
