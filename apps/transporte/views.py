from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.usuarios.models import Vehiculo, Usuario
from apps.ordenes.models import Entrega
from django.contrib import messages
from django.db import IntegrityError, models

@login_required
def lista_vehiculos(request):
    q = request.GET.get('q')
    estado = request.GET.get('estado')
    
    vehiculos = Vehiculo.objects.all().select_related('conductor')
    
    if q:
        vehiculos = vehiculos.filter(
            models.Q(placa__icontains=q) |
            models.Q(tipo__icontains=q) |
            models.Q(conductor__nombres__icontains=q) |
            models.Q(conductor__apellidos__icontains=q)
        )
    
    if estado:
        vehiculos = vehiculos.filter(estado=estado)
        
    return render(request, "transporte/lista.html", {
        "vehiculos": vehiculos,
        "query": q,
        "estado_actual": estado
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
        nuevo_estado = request.POST.get("estado")
        
        # Validación HU-33: No desactivar si tiene entregas activas
        if nuevo_estado in ['mantenimiento', 'fuera_de_servicio'] and vehiculo.estado == 'en_ruta':
            messages.error(request, "No se puede cambiar el estado mientras el vehículo tenga una entrega activa (En Ruta).")
        else:
            # También verificar en el modelo Entrega por si acaso el estado del vehículo no se sincronizó
            entregas_activas = Entrega.objects.filter(vehiculo=vehiculo, estado__in=['pendiente', 'en_ruta']).exists()
            if nuevo_estado != 'disponible' and entregas_activas:
                messages.error(request, "No se puede desactivar el vehículo porque tiene entregas pendientes o en curso.")
            else:
                vehiculo.placa = request.POST.get("placa")
                vehiculo.tipo = request.POST.get("tipo")
                vehiculo.capacidad = request.POST.get("capacidad")
                vehiculo.estado = nuevo_estado
                
                conductor_id = request.POST.get("conductor")
                try:
                    # Si el vehículo ya tiene un conductor, y se está cambiando, hay que verificar
                    nuevo_conductor = Usuario.objects.get(id=conductor_id) if conductor_id else None
                    
                    if nuevo_conductor and nuevo_conductor != vehiculo.conductor:
                        # Si el nuevo conductor tiene entregas activas en otro vehículo (aunque no debería por OneToOne), 
                        # o si el vehículo actual tiene entregas activas, evitamos el cambio si es problemático.
                        # Pero el requisito se enfoca en "No desactivar vehículos con entregas activas".
                        pass
                    
                    vehiculo.conductor = nuevo_conductor
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
    
    # Validación HU-33: No eliminar si tiene entregas activas
    entregas_activas = Entrega.objects.filter(vehiculo=vehiculo, estado__in=['pendiente', 'en_ruta']).exists()
    if entregas_activas:
        messages.error(request, "No se puede eliminar el vehículo porque tiene entregas activas.")
        return redirect("transporte:lista_vehiculos")
        
    placa = vehiculo.placa
    vehiculo.delete()
    messages.success(request, f"Vehículo {placa} eliminado correctamente.")
    return redirect("transporte:lista_vehiculos")

@login_required
def desactivar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, id=id)
    
    # Validación HU-33: No desactivar si tiene entregas activas
    entregas_activas = Entrega.objects.filter(vehiculo=vehiculo, estado__in=['pendiente', 'en_ruta']).exists()
    if entregas_activas:
        messages.error(request, "No se puede desactivar el vehículo porque tiene entregas activas.")
    else:
        vehiculo.estado = 'mantenimiento' # O el estado que represente "desactivado"
        vehiculo.save()
        messages.success(request, f"Vehículo {vehiculo.placa} marcado como no disponible.")
        
    return redirect("transporte:lista_vehiculos")
    return redirect("transporte:lista_vehiculos")
