from functools import lru_cache

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connections, models, router, transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.views.decorators.http import require_POST, require_http_methods

from config.permissions import requiere_funcion
from config.security import _respuesta_no_autorizada, role_required
from config.utils import registrar_actividad
from apps.usuarios.models import Conductor, Usuario
from apps.usuarios.views import admin_required

from .models import ConductorVehiculo, Entrega, Novedad, RespuestaSeguimiento, Seguimiento, Vehiculo


@lru_cache(maxsize=4)
def _tiene_columna_catalogo(db_alias):
    connection = connections[db_alias]
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, Vehiculo._meta.db_table)
    return any(column.name == "codigo_catalogo" for column in columns)


def _vehiculos_con_fallback_seguro():
    db_alias = router.db_for_read(Vehiculo)
    vehiculos = Vehiculo.objects.using(db_alias).all()
    if not _tiene_columna_catalogo(db_alias):
        vehiculos = vehiculos.defer("catalogo")
    return vehiculos


@admin_required
def lista_vehiculos(request):
    id_vehiculo = request.GET.get("id_vehiculo")
    placa = request.GET.get("placa")
    tipo = request.GET.get("tipo")
    estado = request.GET.get("estado")
    conductor = request.GET.get("conductor")
    query = request.GET.get("q", "")

    asignaciones_activas = Prefetch(
        "asignaciones_conductor",
        queryset=(
            ConductorVehiculo.objects.filter(fecha_fin__isnull=True)
            .select_related("conductor__usuario")
            .order_by("-fecha_asignacion")
        ),
        to_attr="asignaciones_activas",
    )
    vehiculos = _vehiculos_con_fallback_seguro().prefetch_related(asignaciones_activas)

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
            models.Q(asignaciones_conductor__fecha_fin__isnull=True)
            & (
                models.Q(asignaciones_conductor__conductor__usuario__nombres__icontains=conductor)
                | models.Q(
                    asignaciones_conductor__conductor__usuario__apellidos__icontains=conductor
                )
            )
        ).distinct()
    if query:
        vehiculos = vehiculos.filter(
            models.Q(placa__icontains=query) | models.Q(tipo_vehiculo__icontains=query)
        )

    filter_fields = [
        {
            "type": "text",
            "name": "placa",
            "placeholder": "Placa",
            "value": placa or "",
            "size": "3",
        },
        {
            "type": "text",
            "name": "tipo",
            "placeholder": "Tipo de vehículo",
            "value": tipo or "",
            "size": "3",
        },
        {
            "type": "select",
            "name": "estado",
            "placeholder": "Estado (Todos)",
            "value": estado or "",
            "size": "3",
            "options": [
                {"value": "disponible", "label": "Disponible", "selected": estado == "disponible"},
                {"value": "en_ruta", "label": "En Ruta", "selected": estado == "en_ruta"},
                {
                    "value": "mantenimiento",
                    "label": "Mantenimiento",
                    "selected": estado == "mantenimiento",
                },
                {
                    "value": "fuera_de_servicio",
                    "label": "Fuera de Servicio",
                    "selected": estado == "fuera_de_servicio",
                },
            ],
        },
    ]

    vehiculos = list(vehiculos)
    for v in vehiculos:
        asignacion = v.asignaciones_activas[0] if v.asignaciones_activas else None
        v.conductor = asignacion.conductor.usuario if asignacion else None

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

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "logistica/_lista_body.html", {"vehiculos": vehiculos})

    return render(request, "logistica/lista.html", context)


@admin_required
def crear_vehiculo(request):
    conductor_activos = ConductorVehiculo.objects.filter(fecha_fin__isnull=True).values_list(
        "conductor__usuario_id", flat=True
    )
    conductores_disponibles = (
        Usuario.objects.filter(rol="conductor", estado="activo", is_active=True)
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
            vehiculo = Vehiculo(
                placa=placa,
                marca=marca,
                modelo=modelo,
                tipo_vehiculo=tipo,
                capacidad_carga=capacidad,
                estado="disponible",
            )
            vehiculo.full_clean()

            if conductor_id:
                conductor_usuario = conductores_disponibles.filter(pk=conductor_id).first()
                if conductor_usuario is None:
                    raise ValueError("El conductor seleccionado no está disponible.")
                conductor_perfil, _ = Conductor.ensure_for_user(conductor_usuario)

            with transaction.atomic():
                vehiculo.save()
                if conductor_id:
                    ConductorVehiculo.objects.create(
                        conductor=conductor_perfil,
                        vehiculo=vehiculo,
                    )
            messages.success(request, f"Vehículo {placa} registrado correctamente.")
            return redirect("logistica:lista_vehiculos")
        except IntegrityError:
            messages.error(
                request, "Error: La placa ya existe o el conductor ya tiene un vehículo."
            )
        except (ValidationError, ValueError):
            messages.error(request, "Revisa los datos del vehículo y el conductor seleccionado.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    context = {"action": "crear", "conductores": conductores_disponibles}

    return render(request, "logistica/form.html", context)


@admin_required
def editar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, pk=id)
    conductores_disponibles = (
        Conductor.objects.filter(estado="activo", usuario__estado="activo", usuario__is_active=True)
        .exclude(
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
            conductor_id = request.POST.get("conductor")
            conductor_perfil = None
            if conductor_id:
                conductor_perfil = conductores.filter(usuario_id=conductor_id).first()
                if conductor_perfil is None:
                    messages.error(request, "El conductor seleccionado no está disponible.")
                    return render(
                        request,
                        "logistica/form.html",
                        {"vehiculo": vehiculo, "action": "editar", "conductores": conductores},
                        status=400,
                    )

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
                capacidad = request.POST.get("capacidad", "").replace(",", ".")
                vehiculo.capacidad_carga = capacidad
                vehiculo.estado = nuevo_estado
                try:
                    vehiculo.full_clean()
                except ValidationError:
                    messages.error(request, "Revisa los datos del vehículo.")
                    return render(
                        request,
                        "logistica/form.html",
                        {"vehiculo": vehiculo, "action": "editar", "conductores": conductores},
                        status=400,
                    )
                vehiculo.save()

                try:
                    ConductorVehiculo.objects.filter(
                        vehiculo=vehiculo, fecha_fin__isnull=True
                    ).update(fecha_fin=now())

                    if conductor_id:
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
@require_POST
def eliminar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, pk=id)

    tiene_historial = Entrega.objects.filter(vehiculo=vehiculo).exists()
    if tiene_historial:
        messages.error(
            request,
            f"No es posible eliminar el vehículo con placa «{vehiculo.placa}» porque cuenta con un historial "
            "de entregas registradas en el sistema. Puedes cambiar su estado a «Fuera de Servicio» o «Mantenimiento».",
        )
        return redirect("logistica:lista_vehiculos")

    placa = vehiculo.placa
    with transaction.atomic():
        vehiculo.asignaciones_conductor.all().delete()
        vehiculo.delete()
        registrar_actividad(
            request,
            "eliminar",
            "vehiculo",
            id,
            f"Admin eliminó vehículo {placa} sin historial de entregas",
        )
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
        messages.error(
            request, "No se puede inhabilitar el vehículo porque tiene entregas activas."
        )
        return redirect("logistica:lista_vehiculos")

    if vehiculo.estado == "fuera_de_servicio":
        vehiculo.estado = "disponible"
        mensaje = "habilitado"
    elif vehiculo.estado == "disponible":
        vehiculo.estado = "fuera_de_servicio"
        mensaje = "inhabilitado"
    else:
        messages.error(
            request, "El vehículo debe finalizar su estado actual antes de cambiar disponibilidad."
        )
        return redirect("logistica:lista_vehiculos")

    vehiculo.save(update_fields=["estado"])
    messages.success(request, f"Vehículo {vehiculo.placa} {mensaje} correctamente.")
    return redirect("logistica:lista_vehiculos")


@admin_required
@require_POST
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
@require_http_methods(["GET", "POST"])
def crear_novedad(request, entrega_id):
    entrega = get_object_or_404(
        Entrega.objects.select_related("pedido", "conductor__usuario"),
        pk=entrega_id,
    )

    es_conductor = request.user.rol == "conductor"
    if es_conductor:
        if (
            entrega.conductor.usuario_id != request.user.pk
            and entrega.conductor_usuario_id != request.user.pk
        ):
            return _respuesta_no_autorizada(request)

    if request.method == "POST":
        tipo = request.POST.get("tipo")
        descripcion = request.POST.get("descripcion", "").strip()

        if not tipo or not descripcion:
            messages.error(request, "El tipo y la descripción de la novedad son obligatorios.")
            return render(
                request,
                "logistica/crear.html",
                {"entrega": entrega, "pedido": entrega.pedido},
                status=400,
            )

        novedad = Novedad(
            entrega=entrega,
            tipo=tipo,
            descripcion=descripcion,
            reportado_por=request.user,
        )
        try:
            novedad.full_clean()
        except ValidationError:
            messages.error(request, "El tipo y la descripción de la novedad no son válidos.")
            return render(
                request,
                "logistica/crear.html",
                {"entrega": entrega, "pedido": entrega.pedido},
                status=400,
            )
        novedad.save()

        registrar_actividad(
            request,
            "crear",
            "novedad",
            novedad.pk,
            f"Novedad «{novedad.get_tipo_display()}» reportada por {request.user.nombre_mostrar} en entrega #{entrega.id_entrega}",
        )

        messages.success(request, "Novedad registrada correctamente.")
        if es_conductor:
            return redirect("logistica:mis_novedades")
        return redirect("logistica:lista_novedades_admin")

    return render(
        request,
        "logistica/crear.html",
        {"entrega": entrega, "pedido": entrega.pedido},
    )


@login_required
@role_required(["conductor", "admin"])
def mis_novedades(request):
    usuario = request.user
    if usuario.rol == "conductor":
        conductor, _ = Conductor.ensure_for_user(usuario)
        novedades = (
            Novedad.objects.filter(entrega__conductor=conductor)
            .select_related("entrega", "entrega__pedido", "reportado_por")
            .prefetch_related("seguimientos__respuesta")
            .order_by("-fecha_generada")
        )
    else:
        novedades = (
            Novedad.objects.select_related(
                "entrega", "entrega__pedido", "reportado_por", "entrega__conductor__usuario"
            )
            .prefetch_related("seguimientos__respuesta")
            .order_by("-fecha_generada")
        )

    estado = request.GET.get("estado", "").strip()
    tipo = request.GET.get("tipo", "").strip()
    if estado:
        novedades = novedades.filter(estado=estado)
    if tipo:
        novedades = novedades.filter(tipo=tipo)

    context = {
        "novedades": novedades,
        "estado_actual": estado,
        "tipo_actual": tipo,
        "tipos": Novedad.TIPOS,
        "estados": Novedad.ESTADOS,
    }
    return render(request, "logistica/mis_novedades.html", context)


@admin_required
def lista_novedades_admin(request):
    novedades = (
        Novedad.objects.select_related(
            "entrega", "entrega__pedido", "reportado_por", "entrega__conductor__usuario"
        )
        .prefetch_related("seguimientos__respuesta")
        .order_by("-fecha_generada")
    )

    estado = request.GET.get("estado", "").strip()
    tipo = request.GET.get("tipo", "").strip()
    query = request.GET.get("q", "").strip()

    if estado:
        novedades = novedades.filter(estado=estado)
    if tipo:
        novedades = novedades.filter(tipo=tipo)
    if query:
        novedades = novedades.filter(
            Q(descripcion__icontains=query)
            | Q(entrega__pedido__codigo_pedido__icontains=query)
            | Q(reportado_por__nombres__icontains=query)
            | Q(reportado_por__apellidos__icontains=query)
        )

    context = {
        "novedades": novedades,
        "estado_actual": estado,
        "tipo_actual": tipo,
        "query": query,
        "tipos": Novedad.TIPOS,
        "estados": Novedad.ESTADOS,
    }
    return render(request, "logistica/lista_novedades.html", context)


@login_required
@requiere_funcion("registrar_novedad")
@require_http_methods(["GET", "POST"])
def agregar_seguimiento(request, novedad_id):
    novedad = get_object_or_404(Novedad, pk=novedad_id)
    if request.method == "POST":
        if (
            request.user.rol == "conductor"
            and novedad.entrega.conductor.usuario_id != request.user.pk
        ):
            return _respuesta_no_autorizada(request)
        seguimiento = Seguimiento(
            novedad=novedad,
            atendido_por=request.user,
            comentario=request.POST.get("comentario", "").strip(),
        )
        try:
            seguimiento.full_clean()
        except ValidationError:
            messages.error(request, "El comentario debe contener texto válido.")
            return render(
                request,
                "logistica/seguimiento.html",
                {"novedad": novedad},
                status=400,
            )
        seguimiento.save()
        if novedad.estado == "abierta":
            novedad.estado = "en_atencion"
            novedad.save(update_fields=["estado"])
        return redirect("logistica:crear_novedad", entrega_id=novedad.entrega_id)
    return render(request, "logistica/seguimiento.html", {"novedad": novedad})


@login_required
@requiere_funcion("responder_seguimiento")
@require_http_methods(["GET", "POST"])
def responder_seguimiento(request, seguimiento_id):
    seg = get_object_or_404(Seguimiento, pk=seguimiento_id)
    if request.method == "POST":
        if hasattr(seg, "respuesta"):
            messages.error(request, "Este seguimiento ya fue respondido.")
            return redirect("pedidos:ver_pedido_admin", id=seg.novedad.entrega.pedido_id)
        respuesta = RespuestaSeguimiento(
            seguimiento=seg,
            redactada_por=request.user,
            texto=request.POST.get("texto", "").strip(),
            estado=request.POST.get("estado", "aceptada"),
        )
        try:
            respuesta.full_clean()
        except ValidationError:
            messages.error(request, "La respuesta contiene datos no válidos.")
            return render(
                request,
                "logistica/responder.html",
                {"seguimiento": seg},
                status=400,
            )
        respuesta.save()
        seg.estado = "respondida"
        seg.save(update_fields=["estado"])
        if seg.novedad.estado == "en_atencion":
            seg.novedad.estado = "cerrada"
            seg.novedad.save(update_fields=["estado"])
        return redirect("pedidos:ver_pedido_admin", id=seg.novedad.entrega.pedido_id)
    return render(request, "logistica/responder.html", {"seguimiento": seg})
