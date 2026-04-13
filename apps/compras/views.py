from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Proveedor, Compra, DetalleCompra
from django.contrib import messages
from historial.utils import registrar_actividad

from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings

@login_required
def contactar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    if request.method == "POST":
        asunto = request.POST.get("asunto")
        mensaje_texto = request.POST.get("mensaje")
        
        # Enviar correo real (usando configuración de settings.py)
        # o simular envío si falla
        try:
            cuerpo_mensaje = f"Mensaje de {request.user.get_full_name()} ({request.user.email}):\n\n{mensaje_texto}"
            send_mail(
                asunto,
                cuerpo_mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [proveedor.email],
                fail_silently=False,
            )
            registrar_actividad(request, 'otro', 'proveedores', proveedor.nit, f"Mensaje enviado a proveedor: {proveedor.nombre}")
            messages.success(request, f"Mensaje enviado a {proveedor.nombre} con éxito.")
        except Exception as e:
            # Si falla el envío real por falta de red, etc., al menos registramos la actividad
            registrar_actividad(request, 'otro', 'proveedores', proveedor.nit, f"Intento de mensaje a {proveedor.nombre} (Falló envío real)")
            messages.info(request, f"Se ha registrado el mensaje para {proveedor.nombre} (Simulación de envío).")

        return redirect("compras:lista_proveedores")
        
    return render(request, "compras/proveedor_contacto.html", {"proveedor": proveedor})

@login_required
def lista_proveedores(request):
    q = request.GET.get('q', '')
    if q:
        proveedores = Proveedor.objects.filter(
            Q(nombre__icontains=q) |
            Q(nit__icontains=q) |
            Q(contacto__icontains=q) |
            Q(telefono__icontains=q) |
            Q(email__icontains=q)
        )
    else:
        proveedores = Proveedor.objects.all()
    return render(request, "compras/proveedores_lista.html", {"proveedores": proveedores, "query": q})

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
