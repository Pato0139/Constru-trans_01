from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Orden
from Usuarios.models import Usuario


@login_required
def lista_ordenes(request):

    ordenes = Orden.objects.all()

    return render(request, "Ordenes/lista_ordenes.html", {
        "ordenes": ordenes
    })


@login_required
def crear_orden(request):

    clientes = Usuario.objects.filter(rol="cliente")
    conductores = Usuario.objects.filter(rol="conductor")

    if request.method == "POST":

        cliente = request.POST.get("cliente")
        conductor = request.POST.get("conductor")
        origen = request.POST.get("origen")
        destino = request.POST.get("destino")

        Orden.objects.create(
            cliente_id=cliente,
            conductor_id=conductor,
            direccion_origen=origen,
            direccion_destino=destino
        )

        return redirect("lista_ordenes")

    return render(request, "Ordenes/crear_orden.html", {
        "clientes": clientes,
        "conductores": conductores
    })