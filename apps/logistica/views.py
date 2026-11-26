from functools import lru_cache
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connections, models, router, transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.http import require_http_methods, require_POST

from apps.usuarios.models import Conductor, Usuario
from apps.pedidos.models import Pedido
from apps.usuarios.views import admin_required
from config.permissions import requiere_funcion
from config.security import _respuesta_no_autorizada, role_required
from config.utils import registrar_actividad
from .forms import NovedadForm, ReagendarEntregaForm, ReasignarRecursosForm
from .services import notificar_evento_logistico, reagendar_entrega, reasignar_recursos_entrega

from .models import (
    MARCAS_VEHICULO,
    ConductorVehiculo,
    Entrega,
    Novedad,
    RespuestaSeguimiento,
    Seguimiento,
    Vehiculo,
)


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

        if marca not in MARCAS_VEHICULO:
            messages.error(request, "Selecciona una marca de vehículo válida de la lista.")
            return render(
                request,
                "logistica/form.html",
                {
                    "action": "crear",
                    "conductores": conductores_disponibles,
                    "marcas": MARCAS_VEHICULO,
                },
            )

        try:
            capacidad_decimal = Decimal(str(capacidad).replace(",", "."))
            if capacidad_decimal < Decimal("5"):
                raise ValueError("La capacidad mínima para registrar un vehículo es 5 toneladas.")
            vehiculo = Vehiculo(
                placa=placa,
                marca=marca,
                modelo=modelo,
                tipo_vehiculo=tipo,
                capacidad_carga=capacidad,
                estado="disponible",
            )
            vehiculo.full_clean()

            conductor_perfil = None
            if conductor_id:
                conductor_usuario = conductores_disponibles.filter(pk=conductor_id).first()
                if conductor_usuario is None:
                    raise ValueError("El conductor seleccionado no está disponible.")
                conductor_perfil, _ = Conductor.ensure_for_user(conductor_usuario)

            with transaction.atomic():
                vehiculo.save()
                if conductor_id and conductor_perfil:
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

    context = {"action": "crear", "conductores": conductores_disponibles, "marcas": MARCAS_VEHICULO}

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
        conductor_id = request.POST.get("conductor") or None
        conductor_actual_id = current_assignment.conductor.usuario_id if current_assignment else None

        entregas_activas = Entrega.objects.filter(
            vehiculo=vehiculo, estado__in=["pendiente", "en_ruta"]
        ).exists()
        if entregas_activas and (
            nuevo_estado != vehiculo.estado or conductor_id != conductor_actual_id
        ):
            messages.error(
                request,
                "No se puede cambiar el estado ni el conductor asignado mientras el vehículo tenga entregas pendientes o en ruta.",
            )
        else:
            conductor_perfil = None
            if conductor_id:
                conductor_perfil = conductores.filter(usuario_id=conductor_id).first()
                if conductor_perfil is None:
                    messages.error(request, "El conductor seleccionado no está disponible.")
                    return render(
                        request,
                        "logistica/form.html",
                        {
                            "vehiculo": vehiculo,
                            "action": "editar",
                            "conductores": conductores,
                            "marcas": MARCAS_VEHICULO,
                        },
                        status=400,
                    )

            if not entregas_activas or (nuevo_estado == vehiculo.estado and conductor_id == conductor_actual_id):
                marca_sel = request.POST.get("marca", "").strip()
                if marca_sel not in MARCAS_VEHICULO:
                    messages.error(
                        request, "Selecciona una marca de vehículo válida de la lista."
                    )
                    return render(
                        request,
                        "logistica/form.html",
                        {
                            "vehiculo": vehiculo,
                            "action": "editar",
                            "conductores": conductores,
                            "marcas": MARCAS_VEHICULO,
                        },
                        status=400,
                    )
                vehiculo.placa = request.POST.get("placa")
                vehiculo.tipo_vehiculo = request.POST.get("tipo")
                vehiculo.marca = marca_sel
                vehiculo.modelo = request.POST.get("modelo", "").strip()
                capacidad = request.POST.get("capacidad", "").replace(",", ".")
                try:
                    capacidad_decimal = Decimal(capacidad)
                    if capacidad_decimal < Decimal("5") and capacidad_decimal != vehiculo.capacidad_carga:
                        raise ValidationError("La capacidad mínima para vehículos nuevos o modificados es 5 toneladas.")
                except (InvalidOperation, ValueError):
                    messages.error(request, "Indica una capacidad válida en toneladas.")
                    return render(
                        request,
                        "logistica/form.html",
                        {"vehiculo": vehiculo, "action": "editar", "conductores": conductores, "marcas": MARCAS_VEHICULO},
                        status=400,
                    )
                vehiculo.capacidad_carga = capacidad
                vehiculo.estado = nuevo_estado
                try:
                    vehiculo.full_clean()
                except ValidationError:
                    messages.error(request, "Revisa los datos del vehículo.")
                    return render(
                        request,
                        "logistica/form.html",
                        {
                            "vehiculo": vehiculo,
                            "action": "editar",
                            "conductores": conductores,
                            "marcas": MARCAS_VEHICULO,
                        },
                        status=400,
                    )
                vehiculo.save()

                try:
                    if conductor_id != conductor_actual_id:
                        ConductorVehiculo.objects.filter(
                            vehiculo=vehiculo, fecha_fin__isnull=True
                        ).update(fecha_fin=now())

                        if conductor_id and conductor_perfil:
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

    context = {"vehiculo": vehiculo, "action": "editar", "conductores": conductores, "marcas": MARCAS_VEHICULO}

    return render(request, "logistica/form.html", context)


@admin_required
@require_POST
def eliminar_vehiculo(request, id):
    vehiculo = get_object_or_404(Vehiculo, pk=id)

    asignacion_activa = ConductorVehiculo.objects.filter(
        vehiculo=vehiculo, fecha_fin__isnull=True
    ).exists()
    if asignacion_activa:
        messages.error(
            request,
            f"No se puede eliminar {vehiculo.placa} mientras siga asignado a un conductor. Libera primero la asignación.",
        )
        return redirect("logistica:lista_vehiculos")

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


@role_required(["conductor", "admin"])
@require_http_methods(["GET", "POST"])
def crear_novedad(request, entrega_id):
    entrega = get_object_or_404(
        Entrega.objects.select_related("pedido", "conductor__usuario"),
        pk=entrega_id,
    )

    es_conductor = request.user.rol == "conductor"
    if es_conductor:
        conductor_asignado = bool(
            (entrega.conductor_id and entrega.conductor.usuario_id == request.user.pk)
            or entrega.conductor_usuario_id == request.user.pk
        )
        if not conductor_asignado:
            return _respuesta_no_autorizada(request)

    form = NovedadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        novedad = form.save(commit=False)
        novedad.entrega = entrega
        novedad.reportado_por = request.user
        novedad.save()
        tipo = novedad.get_tipo_display()
        registrar_actividad(
            request,
            "crear",
            "novedad",
            novedad.pk,
            f"Novedad «{tipo}» registrada en el envío #{entrega.id_entrega}. "
            f"Descripción: {novedad.descripcion}. Acción aplicada: {novedad.solucion or 'Pendiente'}",
        )
        if novedad.tipo in {"demora", "clima", "mecanico", "cliente", "acceso_vias", "mercancia", "ausencia_cliente", "otro"}:
            notificar_evento_logistico("novedad_logistica", entrega.pedido, extra_info=tipo)
        messages.success(request, "Novedad registrada correctamente.")
        if es_conductor:
            return redirect("logistica:mis_novedades")
        return redirect("logistica:lista_novedades_admin")

    return render(
        request,
        "logistica/crear.html",
        {"entrega": entrega, "pedido": entrega.pedido, "form": form},
        status=400 if request.method == "POST" else 200,
    )


@admin_required
@require_http_methods(["GET", "POST"])
def reasignar_entrega(request, pedido_id):
    pedido = get_object_or_404(Pedido, codigo_pedido=pedido_id)
    entrega = pedido.entregas.select_related("conductor__usuario", "vehiculo").first()
    if entrega is None:
        messages.error(request, "El pedido no tiene un envío creado para reasignar.")
        return redirect("pedidos:ver_pedido_admin", id=pedido.codigo_pedido)

    form = ReasignarRecursosForm(request.POST or None, entrega=entrega)
    if request.method == "POST" and form.is_valid():
        motivo = dict(form.fields["motivo"].choices).get(form.cleaned_data["motivo"])
        detalle_motivo = form.cleaned_data["detalle_motivo"].strip()
        try:
            actualizado = reasignar_recursos_entrega(
                entrega.pk,
                conductor_id=form.cleaned_data["conductor"].pk if form.cleaned_data["conductor"] else None,
                vehiculo_id=form.cleaned_data["vehiculo"].pk if form.cleaned_data["vehiculo"] else None,
                motivo=motivo,
                detalle_motivo=detalle_motivo,
            )
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
        else:
            cambio = actualizado._reasignacion
            conductor_anterior = " ".join(cambio["conductor_anterior_nombre"] or []) or "Sin asignar"
            descripcion = (
                f"Reasignación logística. Conductor: {conductor_anterior} → {cambio['conductor_nuevo_nombre']}; "
                f"vehículo: {cambio['vehiculo_anterior_placa'] or 'Sin asignar'} → {cambio['vehiculo_nuevo_placa']}. "
                f"Motivo: {motivo}. {detalle_motivo}".strip()
            )
            registrar_actividad(request, "editar", "pedido", pedido.codigo_pedido, descripcion)
            notificar_evento_logistico(
                "reasignacion",
                actualizado.pedido,
                extra_info=(
                    f"Nuevo conductor: {cambio['conductor_nuevo_nombre']}; "
                    f"vehículo: {cambio['vehiculo_nuevo_placa']}."
                ),
            )
            messages.success(request, "La asignación del envío se actualizó y quedó registrada en el historial.")
            return redirect("pedidos:ver_pedido_admin", id=pedido.codigo_pedido)

    return render(request, "logistica/reasignar.html", {"pedido": pedido, "entrega": entrega, "form": form})


@admin_required
@require_http_methods(["GET", "POST"])
def reagendar_entrega_view(request, pedido_id):
    pedido = get_object_or_404(Pedido, codigo_pedido=pedido_id)
    form = ReagendarEntregaForm(request.POST or None)
    if request.method == "GET" and pedido.fecha_entrega_programada:
        form.fields["fecha_entrega_programada"].initial = pedido.fecha_entrega_programada
    if request.method == "POST" and form.is_valid():
        motivo = dict(form.fields["motivo"].choices).get(form.cleaned_data["motivo"])
        detalle_motivo = form.cleaned_data["detalle_motivo"].strip()
        try:
            actualizado, anterior = reagendar_entrega(
                pedido.pk,
                form.cleaned_data["fecha_entrega_programada"],
                using=pedido._state.db or "default",
            )
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
        else:
            anterior_texto = timezone.localtime(anterior).strftime("%d/%m/%Y %H:%M") if anterior else "Sin programar"
            nueva_texto = timezone.localtime(actualizado.fecha_entrega_programada).strftime("%d/%m/%Y %H:%M")
            descripcion = (
                f"Entrega reagendada: {anterior_texto} → {nueva_texto}. "
                f"Motivo: {motivo}. {detalle_motivo}".strip()
            )
            registrar_actividad(request, "editar", "pedido", pedido.codigo_pedido, descripcion)
            evento_key = (
                f"{anterior.strftime('%Y%m%d%H%M') if anterior else 'sin-fecha'}-"
                f"{actualizado.fecha_entrega_programada.strftime('%Y%m%d%H%M')}"
            )
            notificar_evento_logistico(
                "fecha_reagendada",
                actualizado,
                extra_info=(
                    f"Fecha anterior: {anterior_texto}. Nueva fecha y hora: {nueva_texto}. "
                    f"Motivo: {motivo}. {detalle_motivo} "
                    "El pedido sigue activo y conserva su conductor y vehículo."
                ).strip(),
                using=actualizado._state.db or "default",
                event_key=evento_key,
            )
            messages.success(request, "La nueva fecha quedó guardada y se notificó al cliente.")
            return redirect("pedidos:ver_pedido_admin", id=pedido.codigo_pedido)

    return render(request, "logistica/reagendar.html", {"pedido": pedido, "form": form})


@login_required
@role_required(["conductor", "admin"])
def mis_novedades(request):
    usuario = request.user
    if usuario.rol == "conductor":
        novedades = (
            Novedad.objects.filter(reportado_por=usuario)
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
    if request.user.rol == "conductor":
        conductor_asignado = bool(
            (novedad.entrega.conductor_id and novedad.entrega.conductor.usuario_id == request.user.pk)
            or novedad.entrega.conductor_usuario_id == request.user.pk
        )
        if not conductor_asignado:
            return _respuesta_no_autorizada(request)
    if request.method == "POST":
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
        if request.user.rol == "conductor":
            return redirect("logistica:mis_novedades")
        return redirect("logistica:lista_novedades_admin")
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
