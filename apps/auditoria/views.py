from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.html import format_html

from apps.auditoria.models import Historial
from apps.logistica.models import Entrega, Novedad
from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.usuarios.views import admin_required


def _filtrar_registros(request):
    registros = Historial.objects.select_related("usuario").all()

    usuario = request.GET.get("usuario", "").strip()
    accion = request.GET.get("accion", "").strip()
    modulo = request.GET.get("modulo", "").strip()
    fecha_inicio = parse_date(request.GET.get("fecha_inicio", ""))
    fecha_fin = parse_date(request.GET.get("fecha_fin", ""))

    if usuario:
        registros = registros.filter(
            Q(usuario__username__icontains=usuario)
            | Q(usuario__nombres__icontains=usuario)
            | Q(usuario__apellidos__icontains=usuario)
            | Q(usuario__email__icontains=usuario)
        )
    if accion:
        registros = registros.filter(accion=accion)
    if modulo:
        registros = registros.filter(Q(modulo=modulo) | Q(tabla=modulo))
    if fecha_inicio:
        registros = registros.filter(
            Q(fecha_hora__date__gte=fecha_inicio)
            | Q(fecha_hora__isnull=True, fecha__date__gte=fecha_inicio)
        )
    if fecha_fin:
        registros = registros.filter(
            Q(fecha_hora__date__lte=fecha_fin)
            | Q(fecha_hora__isnull=True, fecha__date__lte=fecha_fin)
        )

    return registros, {
        "usuario": usuario,
        "accion": accion,
        "modulo": modulo,
        "fecha_inicio": request.GET.get("fecha_inicio", "").strip(),
        "fecha_fin": request.GET.get("fecha_fin", "").strip(),
    }


def _resolver_envios(registros):
    """Relaciona acciones con entregas/pedidos sin añadir relaciones al MER."""
    registros = list(registros)
    referencias = {}
    entregas_ids = set()
    pedidos_ids = set()
    pagos_ids = set()
    novedades_ids = set()

    for registro in registros:
        modulo = (registro.modulo or registro.tabla or "").strip().lower()
        raw_id = registro.elemento_id or registro.registro_id
        try:
            elemento_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        referencias[registro.pk] = (modulo, elemento_id)
        if modulo in {"entrega", "entregas", "envio", "envíos"}:
            entregas_ids.add(elemento_id)
        elif modulo in {"pedido", "pedidos"}:
            pedidos_ids.add(elemento_id)
        elif modulo in {"pago", "pagos"}:
            pagos_ids.add(elemento_id)
        elif modulo in {"novedad", "novedades"}:
            novedades_ids.add(elemento_id)

    pago_a_pedido = dict(
        Pago.objects.filter(pk__in=pagos_ids).values_list("pk", "pedido_id")
    )
    pedidos_ids.update(pago_a_pedido.values())
    novedad_a_entrega = dict(
        Novedad.objects.filter(pk__in=novedades_ids).values_list("pk", "entrega_id")
    )
    entregas_ids.update(novedad_a_entrega.values())

    entregas = list(
        Entrega.objects.filter(Q(pk__in=entregas_ids) | Q(pedido_id__in=pedidos_ids))
        .select_related("pedido")
        .order_by("id_entrega")
    )
    entrega_por_id = {entrega.pk: entrega for entrega in entregas}
    entrega_por_pedido = {}
    for entrega in entregas:
        entrega_por_pedido.setdefault(entrega.pedido_id, entrega)

    pedido_codigos = dict(
        Pedido.objects.filter(pk__in=pedidos_ids).values_list("pk", "codigo_pedido")
    )
    resultados = {}
    for registro_id, (modulo, elemento_id) in referencias.items():
        entrega = None
        pedido_id = None
        if modulo in {"entrega", "entregas", "envio", "envíos"}:
            entrega = entrega_por_id.get(elemento_id)
            pedido_id = entrega.pedido_id if entrega else None
        elif modulo in {"pedido", "pedidos"}:
            pedido_id = elemento_id
            entrega = entrega_por_pedido.get(pedido_id)
        elif modulo in {"pago", "pagos"}:
            pedido_id = pago_a_pedido.get(elemento_id)
            entrega = entrega_por_pedido.get(pedido_id)
        elif modulo in {"novedad", "novedades"}:
            entrega = entrega_por_id.get(novedad_a_entrega.get(elemento_id))
            pedido_id = entrega.pedido_id if entrega else None

        if entrega:
            resultados[registro_id] = format_html(
                "#ENV-{} · #CT-{}", entrega.id_entrega, entrega.pedido.codigo_pedido
            )
        elif pedido_id and pedido_id in pedido_codigos:
            resultados[registro_id] = format_html(
                "#CT-{} (sin envío registrado)", pedido_codigos[pedido_id]
            )
        else:
            resultados[registro_id] = "—"

    return resultados


def _fila_json(registro):
    usuario = (
        format_html(
            '<span class="badge bg-info text-dark fw-semibold px-2 py-1 auditoria-user-badge" title="{}">{}</span>',
            registro.usuario.username,
            registro.usuario.username,
        )
        if registro.usuario
        else format_html(
            '<span class="badge bg-secondary text-white px-2 py-1">Sistema/Anónimo</span>'
        )
    )
    estilos_accion = {
        "crear": ("text-success", "bi-plus-circle", "Crear"),
        "editar": ("text-warning", "bi-pencil", "Editar"),
        "desactivar": ("text-warning", "bi-slash-circle", "Desactivar"),
        "eliminar": ("text-danger", "bi-slash-circle", "Inhabilitar"),
        "login": ("text-info", "bi-box-arrow-in-right", "Inicio de sesión"),
        "logout": ("text-secondary", "bi-box-arrow-right", "Cierre de sesión"),
    }
    estilo, icono, etiqueta = estilos_accion.get(
        registro.accion,
        ("text-main", "bi-activity", registro.get_accion_display()),
    )
    accion = format_html(
        '<span class="fw-semibold {}"><i class="bi {} me-1"></i>{}</span>', estilo, icono, etiqueta
    )
    modulo = (registro.modulo or registro.tabla or "—").capitalize()
    modulo_html = format_html('<span class="auditoria-modulo-pill">{}</span>', modulo)
    fecha = registro.fecha_hora or registro.fecha
    if fecha:
        local_dt = timezone.localtime(fecha)
        fecha_txt = format_html(
            '<div class="auditoria-datetime-stack">'
            '<span class="auditoria-time">{}</span>'
            '<span class="auditoria-date">{}</span>'
            '</div>',
            local_dt.strftime("%I:%M %p"),
            local_dt.strftime("%d/%m/%Y"),
        )
    else:
        fecha_txt = "—"
    return [
        registro.pk,
        usuario,
        modulo_html,
        fecha_txt,
        accion,
    ]


@admin_required
def lista_historial(request):
    registros, filtros = _filtrar_registros(request)

    if request.GET.get("format") == "json":
        try:
            draw = max(1, int(request.GET.get("draw", 1)))
            start = max(0, int(request.GET.get("start", 0)))
            length = int(request.GET.get("length", 10))
        except (TypeError, ValueError):
            draw, start, length = 1, 0, 10
        length = min(max(length, 1), 100)

        search_value = request.GET.get("search[value]", "").strip()
        if search_value:
            registros = registros.filter(
                Q(descripcion__icontains=search_value)
                | Q(modulo__icontains=search_value)
                | Q(tabla__icontains=search_value)
                | Q(usuario__username__icontains=search_value)
                | Q(usuario__nombres__icontains=search_value)
                | Q(usuario__apellidos__icontains=search_value)
                | Q(elemento_id__icontains=search_value)
                | Q(registro_id__icontains=search_value)
                | Q(ip_address__icontains=search_value)
                | Q(ip__icontains=search_value)
                | Q(accion__icontains=search_value)
            )

        records_total = Historial.objects.count()
        records_filtered = registros.count()
        columnas = {
            "0": "id",
            "1": "usuario__username",
            "2": "modulo",
            "3": "fecha_hora",
            "4": "accion",
        }
        order_column = request.GET.get("order[0][column]", "3")
        order_field = columnas.get(order_column, "fecha_hora")
        if request.GET.get("order[0][dir]") == "desc":
            order_field = f"-{order_field}"
        registros = registros.order_by(order_field, "-id")
        pagina = list(registros[start : start + length])

        return JsonResponse(
            {
                "draw": draw,
                "recordsTotal": records_total,
                "recordsFiltered": records_filtered,
                "data": [_fila_json(reg) for reg in pagina],
            }
        )

    ordenes = list(registros.order_by("-fecha_hora", "-id")[:10])

    context = {
        "acciones": Historial.ACCIONES,
        "modulos": (
            Historial.objects.exclude(Q(modulo__isnull=True) | Q(modulo=""))
            .order_by("modulo")
            .values_list("modulo", flat=True)
            .distinct()
        ),
        "registros": ordenes,
        "usuario_actual": filtros["usuario"],
        "accion_actual": filtros["accion"],
        "modulo_actual": filtros["modulo"],
        "fecha_inicio_actual": filtros["fecha_inicio"],
        "fecha_fin_actual": filtros["fecha_fin"],
    }
    return render(request, "auditoria/lista.html", context)
