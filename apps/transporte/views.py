from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.usuarios.models import Vehiculo
from .models import Entrega, HistorialEstadoEntrega

# ─── Vehículos ────────────────────────────────────────────────────────────────

@login_required
def lista_vehiculos(request):
    vehiculos = Vehiculo.objects.all()
    return render(request, "transporte/lista.html", {"vehiculos": vehiculos})

@login_required
def crear_vehiculo(request):
    if request.method == "POST":
        Vehiculo.objects.create(
            placa=request.POST.get("placa"),
            tipo=request.POST.get("tipo"),
            capacidad=request.POST.get("capacidad"),
            estado="disponible"
        )
        return redirect("transporte:lista_vehiculos")
    return render(request, "transporte/form.html", {"action": "crear"})

@login_required
def editar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, id=id)
    if request.method == "POST":
        vehiculo.placa = request.POST.get("placa")
        vehiculo.tipo = request.POST.get("tipo")
        vehiculo.capacidad = request.POST.get("capacidad")
        vehiculo.estado = request.POST.get("estado")
        vehiculo.save()
        return redirect("transporte:lista_vehiculos")
    return render(request, "transporte/form.html", {"vehiculo": vehiculo, "action": "editar"})

@login_required
def eliminar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, id=id)
    vehiculo.delete()
    return redirect("transporte:lista_vehiculos")


# ─── Entregas ─────────────────────────────────────────────────────────────────

TRANSICIONES_PERMITIDAS = {
    'pendiente': ['en_camino'],
    'en_camino': ['entregado'],
    'entregado': [],
}

def validar_transicion_estado(estado_actual, estado_nuevo):
    if estado_actual == 'entregado':
        raise ValidationError("No se puede modificar una entrega que ya está en estado 'entregado'.")
    if estado_nuevo not in TRANSICIONES_PERMITIDAS.get(estado_actual, []):
        raise ValidationError(f"Transición no permitida: '{estado_actual}' → '{estado_nuevo}'.")

@login_required
def lista_entregas(request):
    usuario = request.user.usuario
    if usuario.rol == 'admin':
        entregas = Entrega.objects.all()
    else:
        entregas = Entrega.objects.filter(conductor=usuario.nombres + ' ' + usuario.apellidos)
    return render(request, "transporte/lista_entregas.html", {"entregas": entregas})

@login_required
def crear_entrega(request):
    if request.method == "POST":
        Entrega.objects.create(
            conductor=request.POST.get("conductor"),
            vehiculo=request.POST.get("vehiculo"),
            descripcion=request.POST.get("descripcion"),
            estado='pendiente',
        )
        return redirect("transporte:lista_entregas")
    return redirect("transporte:lista_entregas")

@login_required
def editar_entrega(request, id):
    entrega = get_object_or_404(Entrega, id=id)
    if request.method == "POST":
        entrega.conductor = request.POST.get("conductor")
        entrega.vehiculo = request.POST.get("vehiculo")
        entrega.descripcion = request.POST.get("descripcion")
        entrega.save()
        return redirect("transporte:lista_entregas")
    return redirect("transporte:lista_entregas")

@login_required
def eliminar_entrega(request, id):
    entrega = get_object_or_404(Entrega, id=id)
    entrega.delete()
    return redirect("transporte:lista_entregas")

@login_required
def actualizar_estado_entrega(request, id):
    usuario = request.user.usuario
    entrega = get_object_or_404(Entrega, id=id)
    if request.method == "POST":
        estado_nuevo = request.POST.get("estado")
        try:
            validar_transicion_estado(entrega.estado, estado_nuevo)
            estado_anterior = entrega.estado
            entrega.estado = estado_nuevo
            entrega.fecha_ultimo_cambio_estado = timezone.now()
            entrega.save()
            HistorialEstadoEntrega.objects.create(
                entrega=entrega,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                conductor=usuario.nombres + ' ' + usuario.apellidos,
            )
            return redirect("transporte:lista_entregas")
        except ValidationError:
            return redirect("transporte:lista_entregas")
    return redirect("transporte:lista_entregas")