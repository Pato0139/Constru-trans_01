from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from usuarios.views import admin_required
from .models import Historial


@admin_required
def lista_historial(request):
    if request.GET.get("format") == "json":
        # DataTables server-side parameters
        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 10))

        # Base query with select_related to optimize query count
        registros = Historial.objects.select_related("usuario").all()

        # Custom Filters
        usuario_q = request.GET.get("usuario")
        accion_q = request.GET.get("accion")
        modulo_q = request.GET.get("modulo")
        fecha_inicio = request.GET.get("fecha_inicio")
        fecha_fin = request.GET.get("fecha_fin")

        if usuario_q:
            registros = registros.filter(usuario__username__icontains=usuario_q)
        if accion_q:
            registros = registros.filter(accion=accion_q)
        if modulo_q:
            registros = registros.filter(modulo=modulo_q)
        if fecha_inicio:
            registros = registros.filter(fecha_hora__date__gte=fecha_inicio)
        if fecha_fin:
            registros = registros.filter(fecha_hora__date__lte=fecha_fin)

        # Global search (from DataTable search bar)
        search_value = request.GET.get("search[value]")
        if search_value:
            registros = registros.filter(
                Q(descripcion__icontains=search_value) |
                Q(modulo__icontains=search_value) |
                Q(usuario__username__icontains=search_value) |
                Q(elemento_id__icontains=search_value) |
                Q(ip_address__icontains=search_value)
            )

        # Totals
        records_total = Historial.objects.count()
        records_filtered = registros.count()

        # Ordering
        order_column_idx = request.GET.get("order[0][column]")
        order_dir = request.GET.get("order[0][dir]", "desc")

        columns_mapping = {
            "0": "id",
            "1": "usuario__username",
            "2": "accion",
            "3": "modulo",
            "4": "elemento_id",
            "5": "descripcion",
            "6": "fecha_hora",
            "7": "ip_address",
        }

        order_field = columns_mapping.get(order_column_idx, "fecha_hora")
        if order_dir == "desc":
            order_field = f"-{order_field}"

        registros = registros.order_by(order_field)

        # Pagination
        registros_page = registros[start:start + length]

        # Formatting data
        data = []
        for reg in registros_page:
            # Formatting user
            if reg.usuario:
                usuario_html = f'<span class="badge bg-info text-dark">{reg.usuario.username}</span>'
            else:
                usuario_html = '<span class="badge" style="background-color: rgba(255,255,255,0.2); color: #ffffff;">Sistema/Anónimo</span>'

            # Formatting action
            if reg.accion == 'crear':
                accion_html = '<span class="text-success"><i class="bi bi-plus-circle me-1"></i>Crear</span>'
            elif reg.accion == 'editar':
                accion_html = '<span class="text-warning"><i class="bi bi-pencil me-1"></i>Editar</span>'
            elif reg.accion == 'eliminar':
                accion_html = '<span class="text-danger"><i class="bi bi-trash me-1"></i>Eliminar</span>'
            elif reg.accion == 'login':
                accion_html = '<span class="text-info"><i class="bi bi-box-arrow-in-right me-1"></i>Login</span>'
            elif reg.accion == 'logout':
                accion_html = '<span class="text-secondary"><i class="bi bi-box-arrow-right me-1"></i>Logout</span>'
            else:
                accion_html = reg.get_accion_display()

            data.append([
                reg.id,
                usuario_html,
                accion_html,
                reg.modulo.capitalize() if reg.modulo else "-",
                reg.elemento_id or "-",
                f'<small>{reg.descripcion}</small>',
                reg.fecha_hora.strftime("%Y-m-d %H:%M") if reg.fecha_hora else "",
                f'<small class="text-muted">{reg.ip_address or "-"}</small>'
            ])

        return JsonResponse({
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": data
        })

    # Normal render (empty tbody, handled by Ajax DataTable)
    context = {
        "acciones": Historial.ACCIONES,
        "modulos": Historial.objects.values_list("modulo", flat=True).distinct(),
    }
    return render(request, "historial/lista.html", context)

