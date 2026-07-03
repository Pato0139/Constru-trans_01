from django.contrib import messages
from django.db import IntegrityError, models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now

from ordenes.models import Entrega
from usuarios.models import Conductor, ConductorVehiculo, Usuario, Vehiculo
from usuarios.views import admin_required


@admin_required
def lista_vehiculos(request):
    q = request.GET.get("q")
    estado = request.GET.get("estado")

    vehiculos = Vehiculo.objects.all()

    if q:
        vehiculos = vehiculos.filter(
            models.Q(placa__icontains=q)
            | models.Q(tipo_vehiculo__icontains=q)
            | models.Q(marca__icontains=q)
            | models.Q(modelo__icontains=q)
        )

    if estado:
        vehiculos = vehiculos.filter(estado=estado)

    page = int(request.GET.get("page", 1))
    per_page = 20
    total = vehiculos.count()

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)
    pages_list = list(range(start_page, end_page + 1))

    vehiculos = vehiculos[(page - 1) * per_page : page * per_page]

    context = {
        "vehiculos": vehiculos,
        "query": q,
        "estado_actual": estado,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "pages_list": pages_list,
    }

    return render(request, "transporte/lista.html", context)


@admin_required
def crear_vehiculo(request):
    # Conductores sin vehículo asignado
    conductor_activos = ConductorVehiculo.objects.filter(fecha_fin__isnull=True).values_list(
        "conductor__usuario_id", flat=True
    )
    conductores_disponibles = (
        Usuario.objects.filter(rol="conductor")
        .exclude(id__in=conductor_activos)
        .order_by("nombres", "apellidos")
    )

    if request.method == "POST":
        placa = request.POST.get("placa")
        tipo = request.POST.get("tipo")
        marca = request.POST.get("marca", "").strip()
        modelo = request.POST.get("modelo", "").strip()
        capacidad = request.POST.get("capacidad")
        conductor_id = request.POST.get("conductor")

        try:
            vehiculo = Vehiculo.objects.create(
                placa=placa,
                marca=marca,
                modelo=modelo,
                tipo_vehiculo=tipo,
                capacidad_carga=capacidad,
                estado="disponible"
            )

            if conductor_id:
                conductor_perfil, _ = Conductor.objects.get_or_create(
                    usuario_id=conductor_id,
                    defaults={
                        "numero_licencia": f"PEND-{conductor_id}",
                        "categoria_licencia": "N/A",
                        "fecha_vencimiento_licencia": now().date(),
                        "estado": "activo",
                    },
                )
                ConductorVehiculo.objects.create(conductor=conductor_perfil, vehiculo=vehiculo)

            messages.success(request, f"Vehículo {placa} registrado correctamente.")
            return redirect("transporte:lista_vehiculos")
        except IntegrityError:
            messages.error(
                request, "Error: La placa ya existe o el conductor ya tiene un vehículo."
            )
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    context = {"action": "crear", "conductores": conductores_disponibles}

    return render(request, "transporte/form.html", context)


@admin_required
def editar_vehiculo(request, id):
    from usuarios.models import Conductor

    vehiculo = get_object_or_404(Vehiculo, pk=id)
    # Conductores sin vehículo asignado
    conductores_disponibles = (
        Conductor.objects.exclude(
            usuario_id__in=ConductorVehiculo.objects.filter(fecha_fin__isnull=True).values_list(
                "conductor__usuario_id", flat=True
            )
        )
        .select_related("usuario")
        .order_by("usuario__nombres", "usuario__apellidos")
    )

    # Obtener conductor actual del vehículo
    current_assignment = (
        ConductorVehiculo.objects.filter(vehiculo=vehiculo, fecha_fin__isnull=True)
        .select_related("conductor__usuario")
        .first()
    )
    if current_assignment:
        conductores = (
            conductores_disponibles | Conductor.objects.filter(pk=current_assignment.conductor.pk)
        ).distinct()
    else:
        conductores = conductores_disponibles

    if request.method == "POST":
        nuevo_estado = request.POST.get("estado")

        # Validación
        if nuevo_estado in ["mantenimiento", "fuera_de_servicio"] and vehiculo.estado == "en_ruta":
            messages.error(
                request,
                "No se puede cambiar el estado mientras el vehículo tenga una entrega activa (En Ruta).",
            )
        else:
            entregas_activas = Entrega.objects.filter(
                vehiculo=vehiculo, estado__in=["pendiente", "en_ruta"]
            ).exists()
            if nuevo_estado != "disponible" and entregas_activas:
                messages.error(
                    request,
                    "No se puede desactivar el vehículo porque tiene entregas pendientes o en curso.",
                )
            else:
                vehiculo.placa = request.POST.get("placa")
                vehiculo.tipo_vehiculo = request.POST.get("tipo")
                vehiculo.marca = request.POST.get("marca", "").strip()
                vehiculo.modelo = request.POST.get("modelo", "").strip()
                vehiculo.capacidad_carga = request.POST.get("capacidad").replace(",", ".")
                vehiculo.estado = nuevo_estado
                vehiculo.save()

                conductor_id = request.POST.get("conductor")
                try:
                    ConductorVehiculo.objects.filter(
                        vehiculo=vehiculo, fecha_fin__isnull=True
                    ).update(fecha_fin=now())

                    if conductor_id:
                        conductor_perfil, _ = Conductor.objects.get_or_create(
                            usuario_id=conductor_id,
                            defaults={
                                "numero_licencia": f"PEND-{conductor_id}",
                                "categoria_licencia": "N/A",
                                "fecha_vencimiento_licencia": now().date(),
                                "estado": "activo",
                            },
                        )
                        ConductorVehiculo.objects.create(
                            conductor=conductor_perfil, vehiculo=vehiculo
                        )

                    messages.success(request, f"Vehículo {vehiculo.placa} actualizado.")
                    return redirect("transporte:lista_vehiculos")
                except IntegrityError:
                    messages.error(
                        request, "Error: La placa ya existe o el conductor ya tiene un vehículo."
                    )
                except Exception as e:
                    messages.error(request, f"Error: {str(e)}")

    context = {"vehiculo": vehiculo, "action": "editar", "conductores": conductores}

    return render(request, "transporte/form.html", context)


@admin_required
def eliminar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, pk=id)

    # Validación
    entregas_activas = Entrega.objects.filter(
        vehiculo=vehiculo, estado__in=["pendiente", "en_ruta"]
    ).exists()
    if entregas_activas:
        messages.error(request, "No se puede eliminar el vehículo porque tiene entregas activas.")
        return redirect("transporte:lista_vehiculos")

    placa = vehiculo.placa
    vehiculo.delete()
    messages.success(request, f"Vehículo {placa} eliminado correctamente.")
    return redirect("transporte:lista_vehiculos")


@admin_required
def desactivar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, pk=id)

    # Validación
    entregas_activas = Entrega.objects.filter(
        vehiculo=vehiculo, estado__in=["pendiente", "en_ruta"]
    ).exists()
    if entregas_activas:
        messages.error(request, "No se puede desactivar el vehículo porque tiene entregas activas.")
    else:
        vehiculo.estado = "mantenimiento"
        vehiculo.save()
        messages.success(request, f"Vehículo {vehiculo.placa} marcado como no disponible.")

    return redirect("transporte:lista_vehiculos")
