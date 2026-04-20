from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.usuarios.models import Vehiculo, Usuario
from django.contrib import messages
from django.db import IntegrityError, models

@login_required
def lista_vehiculos(request):
    vehiculos = Vehiculo.objects.all().select_related('conductor')
    return render(request, "transporte/lista.html", {
        "vehiculos": vehiculos
    })

@login_required
def crear_vehiculo(request):
    # Conductores sin vehículo asignado
    conductores = Usuario.objects.filter(rol='conductor', vehiculo_asignado__isnull=True)
    
    if request.method == "POST":
        placa = request.POST.get("placa")
        tipo = request.POST.get("tipo")
        capacidad = request.POST.get("capacidad")
        conductor_id = request.POST.get("conductor")
        
        try:
            conductor = Usuario.objects.get(id=conductor_id) if conductor_id else None
            Vehiculo.objects.create(
                placa=placa,
                tipo=tipo,
                capacidad=capacidad,
                estado="disponible",
                conductor=conductor
            )
            messages.success(request, f"Vehículo {placa} registrado correctamente.")
            return redirect("transporte:lista_vehiculos")
        except IntegrityError:
            messages.error(request, "Error: La placa ya existe o el conductor ya tiene un vehículo.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            
    return render(request, "transporte/form.html", {
        "action": "crear",
        "conductores": conductores
    })

@login_required
def editar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, id=id)
    # Conductores sin vehículo asignado + el conductor actual del vehículo
    conductores = Usuario.objects.filter(
        models.Q(rol='conductor', vehiculo_asignado__isnull=True) | 
        models.Q(id=vehiculo.conductor.id if vehiculo.conductor else None)
    ).distinct()

    if request.method == "POST":
        vehiculo.placa = request.POST.get("placa")
        vehiculo.tipo = request.POST.get("tipo")
        vehiculo.capacidad = request.POST.get("capacidad")
        vehiculo.estado = request.POST.get("estado")
        
        conductor_id = request.POST.get("conductor")
        try:
            vehiculo.conductor = Usuario.objects.get(id=conductor_id) if conductor_id else None
            vehiculo.save()
            messages.success(request, f"Vehículo {vehiculo.placa} actualizado.")
            return redirect("transporte:lista_vehiculos")
        except IntegrityError:
            messages.error(request, "Error: La placa ya existe o el conductor ya tiene un vehículo.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return render(request, "transporte/form.html", {
        "vehiculo": vehiculo, 
        "action": "editar",
        "conductores": conductores
    })

@login_required
def eliminar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, id=id)
    placa = vehiculo.placa
    vehiculo.delete()
    messages.success(request, f"Vehículo {placa} eliminado correctamente.")
    return redirect("transporte:lista_vehiculos")
