from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now

from core.permissions import requiere_funcion
from usuarios.models import Conductor, Usuario
from usuarios.views import admin_required
from .models import (
    Vehiculo,
    ConductorVehiculo,
    Entrega,
    Novedad,
    Seguimiento,
    RespuestaSeguimiento,
)


def _vehiculos_con_fallback_seguro():
    from django.db.utils import ProgrammingError

    base_qs = Vehiculo.objects.all().defer("catalogo")

    try:
        from django.db import connections
        for alias in ("default", "remota"):
            if alias not in connections.databases:
                continue
            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = %s AND column_name = %s",
                        ["vehiculo", "codigo_catalogo"],
                    )
                    has_column = cursor.fetchone() is not None
            except Exception:
                has_column = False
            if alias == "default" and not has_column:
                return base_qs
    except (ProgrammingError, Exception):
        return base_qs

    return Vehiculo.objects.all()


@admin_required
def lista_vehiculos(request):
    id_vehiculo = request.GET.get("id_vehiculo")
    placa = request.GET.get("placa")
    tipo = request.GET.get("tipo")
    estado = request.GET.get("estado")
    conductor = request.GET.get("conductor")
    query = request.GET.get("q", "")

    vehiculos = _vehiculos_con_fallback_seguro()

    if id_vehiculo and id_vehiculo.isdigit():
        vehiculos = vehiculos.filter(id_vehiculo=int(id_vehiculo))
    if placa:
        vehiculos = vehiculos.filter(placa__icontains=placa)
    if tipo:
        vehiculos = vehiculos.filter(tipo_vehiculo__icontains=tipo)
    if estado:
        vehiculos = vehiculos.filter(estado=estado)
    if conductor:
        vehiculos = vehiculos.filter(
            models.Q(asignaciones_conductor__fecha_fin__isnull=True) & (
                models.Q(asignaciones_conductor__conductor__usuario__nombres__icontains=conductor) |
                models.Q(asignaciones_conductor__conductor__usuario__apellidos__icontains=conductor)
            )
        ).distinct()
    if query:
        vehiculos = vehiculos.filter(
            models.Q(placa__icontains=query)
            | models.Q(tipo_vehiculo__icontains=query)
        )

    filter_fields = [
        {"type": "text", "name": "placa", "placeholder": "Placa", "value": placa or "", "size": "3"},
        {"type": "text", "name": "tipo", "placeholder": "Tipo de vehículo", "value": tipo or "", "size": "3"},
        {
            "type": "select",
            "name": "estado",
            "placeholder": "Estado (Todos)",
            "value": estado or "",
            "size": "3",
            "options": [
                {"value": "disponible", "label": "Disponible", "selected": estado == "disponible"},
                {"value": "en_ruta", "label": "En Ruta", "selected": estado == "en_ruta"},
                {"value": "mantenimiento", "label": "Mantenimiento", "selected": estado == "mantenimiento"},
            ],
        },
    ]

    from django.db.utils import ProgrammingError as _PgError

    try:
        vehiculos = list(vehiculos)
    except _PgError as exc:
        if "codigo_catalogo" in str(exc):
            vehiculos = list(Vehiculo.objects.all().defer("catalogo"))
        else:
            raise
    for v in vehiculos:
        v.conductor = v.conductor_actual

    context = {
        "vehiculos": vehiculos,
        "id_vehiculo": id_vehiculo,
        "placa": placa,
        "tipo": tipo,
        "estado_actual": estado,
        "conductor": conductor,
        "query": query,
        "filter_fields": filter_fields,
        "has_filters": any([id_vehiculo, placa, tipo, estado, conductor, query]),
    }

    return render(request, "logistica/lista.html", context)


@admin_required
def crear_vehiculo(request):
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
                conductor_perfil, _ = Conductor.ensure_for_user(
                    Usuario.objects.get(pk=conductor_id)
                )
                ConductorVehiculo.objects.create(conductor=conductor_perfil, vehiculo=vehiculo)

            messages.success(request, f"Vehículo {placa} registrado correctamente.")
            return redirect("logistica:lista_vehiculos")
        except IntegrityError:
            messages.error(
                request, "Error: La placa ya existe o el conductor ya tiene un vehículo."
            )
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    context = {"action": "crear", "conductores": conductores_disponibles}

    return render(request, "logistica/form.html", context)


@admin_required
def editar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, pk=id)
    conductores_disponibles = (
        Conductor.objects.exclude(
            usuario_id__in=ConductorVehiculo.objects.filter(fecha_fin__isnull=True).values_list(
                "conductor__usuario_id", flat=True
            )
        )
        .select_related("usuario")
        .order_by("usuario__nombres", "usuario__apellidos")
    )

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
                        conductor_perfil, _ = Conductor.ensure_for_user(
                            Usuario.objects.get(pk=conductor_id)
                        )
                        ConductorVehiculo.objects.create(
                            conductor=conductor_perfil, vehiculo=vehiculo
                        )

                    messages.success(request, f"Vehículo {vehiculo.placa} actualizado.")
                    return redirect("logistica:lista_vehiculos")
                except IntegrityError:
                    messages.error(
                        request, "Error: La placa ya existe o el conductor ya tiene un vehículo."
                    )
                except Exception as e:
                    messages.error(request, f"Error: {str(e)}")

    context = {"vehiculo": vehiculo, "action": "editar", "conductores": conductores}

    return render(request, "logistica/form.html", context)


@admin_required
def eliminar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, pk=id)

    entregas_activas = Entrega.objects.filter(
        vehiculo=vehiculo, estado__in=["pendiente", "en_ruta"]
    ).exists()
    if entregas_activas:
        messages.error(request, "No se puede eliminar el vehículo porque tiene entregas activas.")
        return redirect("logistica:lista_vehiculos")

    placa = vehiculo.placa
    vehiculo.delete()
    messages.success(request, f"Vehículo {placa} eliminado correctamente.")
    return redirect("logistica:lista_vehiculos")


@admin_required
def cambiar_disponibilidad_vehiculo(request, id):
    if request.method != "POST":
        messages.error(request, "La disponibilidad debe actualizarse mediante POST.")
        return redirect("logistica:lista_vehiculos")

    vehiculo = get_object_or_404(Vehiculo, pk=id)
    entregas_activas = Entrega.objects.filter(
        vehiculo=vehiculo, estado__in=["pendiente", "en_ruta"]
    ).exists()
    if entregas_activas:
        messages.error(request, "No se puede inhabilitar el vehículo porque tiene entregas activas.")
        return redirect("logistica:lista_vehiculos")

    if vehiculo.estado == "fuera_de_servicio":
        vehiculo.estado = "disponible"
        mensaje = "habilitado"
    elif vehiculo.estado == "disponible":
        vehiculo.estado = "fuera_de_servicio"
        mensaje = "inhabilitado"
    else:
        messages.error(request, "El vehículo debe finalizar su estado actual antes de cambiar disponibilidad.")
        return redirect("logistica:lista_vehiculos")

    vehiculo.save(update_fields=["estado"])
    messages.success(request, f"Vehículo {vehiculo.placa} {mensaje} correctamente.")
    return redirect("logistica:lista_vehiculos")


@admin_required
def desactivar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, pk=id)

    entregas_activas = Entrega.objects.filter(
        vehiculo=vehiculo, estado__in=["pendiente", "en_ruta"]
    ).exists()
    if entregas_activas:
        messages.error(request, "No se puede desactivar el vehículo porque tiene entregas activas.")
    else:
        vehiculo.estado = "mantenimiento"
        vehiculo.save()
        messages.success(request, f"Vehículo {vehiculo.placa} marcado como no disponible.")

    return redirect("logistica:lista_vehiculos")


@login_required
@requiere_funcion("registrar_novedad")
def crear_novedad(request, entrega_id):
    entrega = get_object_or_404(
        Entrega.objects.select_related("pedido"),
        pk=entrega_id,
    )
    if request.method == "POST":
        Novedad.objects.create(
            entrega=entrega,
            tipo=request.POST.get("tipo"),
            descripcion=request.POST.get("descripcion"),
            reportado_por=request.user,
        )
        messages.success(request, "Novedad registrada.")
        return redirect("pedidos:ver_pedido_admin", id=entrega.pedido_id)
    return render(
        request,
        "logistica/crear.html",
        {"entrega": entrega, "pedido": entrega.pedido},
    )


@login_required
def agregar_seguimiento(request, novedad_id):
    novedad = get_object_or_404(Novedad, pk=novedad_id)
    if request.method == "POST":
        Seguimiento.objects.create(
            novedad=novedad,
            atendido_por=request.user,
            comentario=request.POST.get("comentario"),
        )
        if novedad.estado == "abierta":
            novedad.estado = "en_atencion"
            novedad.save(update_fields=["estado"])
        return redirect("logistica:crear_novedad", entrega_id=novedad.entrega_id)
    return render(request, "logistica/seguimiento.html", {"novedad": novedad})


@login_required
@requiere_funcion("responder_seguimiento")
def responder_seguimiento(request, seguimiento_id):
    seg = get_object_or_404(Seguimiento, pk=seguimiento_id)
    if request.method == "POST":
        RespuestaSeguimiento.objects.create(
            seguimiento=seg,
            redactada_por=request.user,
            texto=request.POST.get("texto"),
            estado=request.POST.get("estado", "aceptada"),
        )
        seg.estado = "respondida"
        seg.save(update_fields=["estado"])
        if seg.novedad.estado == "en_atencion":
            seg.novedad.estado = "cerrada"
            seg.novedad.save(update_fields=["estado"])
        return redirect("pedidos:ver_pedido_admin", id=seg.novedad.entrega.pedido_id)
    return render(request, "logistica/responder.html", {"seguimiento": seg})
