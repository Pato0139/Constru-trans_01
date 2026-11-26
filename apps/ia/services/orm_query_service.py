import logging
import re

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Q, Sum

logger = logging.getLogger(__name__)

ESTADO_PEDIDO = {
    "pendiente": "Pendiente",
    "autorizado_despacho": "Autorizado para despacho",
    "vehiculo_asignado": "Vehículo asignado",
    "en_ruta": "En ruta",
    "entregado": "Entregado",
    "cancelado": "Cancelado",
}

ROLES_ADMIN = {"admin", "empleado", "administrador"}


def _es_admin(usuario) -> bool:
    if not usuario or not getattr(usuario, "is_authenticated", False):
        return False
    return bool(
        getattr(usuario, "is_superuser", False)
        or getattr(usuario, "rol", None) in ROLES_ADMIN
    )


def _format_number(value):
    try:
        entero, _, decimal = f"{value:.2f}".partition(".")
        entero = f"{int(entero):,}".replace(",", ".")
        return f"{entero},{decimal}" if decimal != "00" else entero
    except (TypeError, ValueError):
        return str(value or 0)


def _extraer_codigo_pedido(mensaje):
    match = re.search(
        r"(?:pedido|orden)\s*(?:n[úu]mero|n[º°]|#)?\s*(\d+)", mensaje or "", re.IGNORECASE
    )
    if not match:
        match = re.search(r"\b(\d{1,6})\b", mensaje or "")
    return int(match.group(1)) if match else None


def consultar_pedido(codigo, usuario=None):
    from apps.pedidos.models import Pedido

    qs = (
        Pedido.objects.filter(codigo_pedido=codigo)
        .select_related("cliente__usuario", "usuario", "conductor__usuario", "pago")
        .prefetch_related("detalles__material", "entregas__vehiculo")
    )
    if usuario and getattr(usuario, "is_authenticated", False) and not _es_admin(usuario):
        rol = getattr(usuario, "rol", "")
        if rol == "conductor":
            qs = qs.filter(Q(conductor__usuario=usuario) | Q(entregas__conductor__usuario=usuario))
        else:
            qs = qs.filter(Q(usuario=usuario) | Q(cliente__usuario=usuario))

    pedido = qs.first()
    if not pedido:
        return None

    detalles = []
    for detalle in pedido.detalles.all()[:10]:
        try:
            detalles.append(
                f"- {detalle.material.nombre}: "
                f"{detalle.cantidad} x ${_format_number(detalle.precio_unitario)}"
            )
        except ObjectDoesNotExist:
            logger.warning("Detalle %s sin material para pedido %s", detalle.pk, codigo)

    cliente_nombre = "Sin cliente"
    if pedido.cliente_id and getattr(pedido.cliente, "usuario", None):
        u = pedido.cliente.usuario
        cliente_nombre = f"{u.nombres} {u.apellidos}".strip() or u.username
    elif pedido.usuario_id:
        cliente_nombre = f"{pedido.usuario.nombres} {pedido.usuario.apellidos}".strip() or pedido.usuario.username

    partes = [
        f"Pedido #{pedido.codigo_pedido}",
        f"Estado: {ESTADO_PEDIDO.get(pedido.estado, pedido.estado)}",
        f"Cliente: {cliente_nombre}",
        f"Total: ${_format_number(pedido.total)}",
        "Materiales: " + ("; ".join(detalles) if detalles else "sin detalles registrados"),
    ]
    pago = getattr(pedido, "pago", None)
    if pago:
        partes.append(f"Pago: {pago.get_metodo_display()} — {pago.get_estado_display()}")
    entrega = pedido.entregas.first()
    if entrega and entrega.vehiculo:
        partes.append(f"Vehículo asignado: {entrega.vehiculo.placa} ({entrega.vehiculo.tipo_vehiculo})")
    if pedido.conductor_id and getattr(pedido.conductor, "usuario", None):
        cu = pedido.conductor.usuario
        partes.append(f"Conductor: {cu.nombres} {cu.apellidos}".strip())
    if pedido.fecha_entrega_programada:
        partes.append(
            f"Entrega programada: {pedido.fecha_entrega_programada.strftime('%d/%m/%Y %H:%M')}"
        )
    if pedido.direccion_destino:
        partes.append(f"Destino: {pedido.direccion_destino}")
    return "\n".join(partes)


def consultar_materiales(mensaje):
    from apps.catalogo.models import MaterialConstruccion

    query = re.sub(
        r"(cuales|cuáles|qué|que|materiales|material|tienes|hay|manejan|lista|catalogo|catálogo|precio|precios|inventario|stock|disponible|disponibles|de|del|en|el|la|los|las)",
        " ",
        mensaje or "",
        flags=re.IGNORECASE,
    )
    query = re.sub(r"[^\w\s]", "", query).strip()
    materiales = MaterialConstruccion.objects.filter(activo=True).select_related(
        "unidad_medida", "marca", "stock"
    )
    if 3 <= len(query) <= 60:
        filtrados = materiales.filter(Q(nombre__icontains=query) | Q(marca__nombre__icontains=query))
        if filtrados.exists():
            materiales = filtrados
    materiales = list(materiales[:15])
    if not materiales:
        return "No hay materiales registrados que coincidan con tu búsqueda."
    lineas = []
    for material in materiales:
        stock_txt = ""
        try:
            if getattr(material, "stock", None) is not None:
                stock_txt = f" | Stock: {material.stock.cantidad_actual}"
        except ObjectDoesNotExist:
            pass
        marca_txt = f" [{material.marca.nombre}]" if material.marca_id else ""
        lineas.append(
            f"- {material.nombre}{marca_txt} ({material.unidad_medida}): ${_format_number(material.precio_referencia)}{stock_txt}"
        )
    return "Materiales del catálogo:\n" + "\n".join(lineas)


def consultar_stock_y_movimientos(mensaje, usuario=None):
    from apps.catalogo.models import Stock
    from apps.catalogo.models.movimientos import MovimientoInventario

    m = (mensaje or "").lower()
    if any(k in m for k in ["movimiento", "kardex", "entradas", "salidas"]):
        if usuario and getattr(usuario, "is_authenticated", False) and not _es_admin(usuario):
            return "El historial de movimientos de inventario solo está disponible para administradores."
        movs = list(
            MovimientoInventario.objects.select_related("material", "usuario")
            .order_by("-fecha")[:8]
        )
        if not movs:
            return "No hay movimientos de inventario registrados todavía."
        return "Últimos movimientos de inventario:\n" + "\n".join(
            f"- [{mv.tipo_movimiento.upper()}] {mv.material.nombre}: {mv.cantidad} ({mv.observacion or 'Sin observación'})"
            for mv in movs
        )

    if any(k in m for k in ["stock bajo", "stock critico", "stock crítico", "agotado", "faltante", "minimo", "mínimo"]):
        bajos = list(
            Stock.objects.filter(cantidad_actual__lte=F("stock_minimo"))
            .select_related("material")[:15]
        )
        if not bajos:
            return "Todo el inventario está por encima del stock mínimo. No hay materiales en alerta."
        return f"Materiales con stock crítico ({len(bajos)}):\n" + "\n".join(
            f"- {s.material.nombre}: actual {s.cantidad_actual} / mínimo {s.stock_minimo}"
            for s in bajos
        )
    return None


def consultar_catalogo_marcas_unidades(mensaje):
    from apps.catalogo.models import Catalogo, Marca, UnidadMedida

    m = (mensaje or "").lower()
    if any(k in m for k in ["marca", "marcas"]):
        marcas = list(Marca.objects.filter(activo=True).order_by("nombre")[:20])
        if not marcas:
            return "No hay marcas activas registradas."
        return f"Marcas registradas ({len(marcas)}):\n" + ", ".join(x.nombre for x in marcas)

    if any(k in m for k in ["unidad de medida", "unidades de medida", "unidades"]):
        unidades = list(UnidadMedida.objects.filter(activa=True).order_by("nombre")[:20])
        if not unidades:
            return "No hay unidades de medida activas registradas."
        return "Unidades de medida activas:\n" + "\n".join(
            f"- {u.nombre} ({u.abreviatura or u.codigo})" for u in unidades
        )

    if any(k in m for k in ["tipo de material", "tipos de material", "categorias", "categorías"]):
        cats = list(Catalogo.objects.filter(activo=True).order_by("nombre_empresa")[:20])
        if not cats:
            return "No hay categorías de catálogo activas."
        return "Tipos de material / Catálogos activos:\n" + "\n".join(
            f"- {c.nombre_empresa} ({c.codigo_catalogo})" for c in cats
        )
    return None


def consultar_pedidos_cliente(mensaje, usuario):
    from apps.pedidos.models import Pedido

    consulta = Pedido.objects.all().order_by("-fecha_solicitud")
    if usuario and getattr(usuario, "is_authenticated", False) and not _es_admin(usuario):
        if getattr(usuario, "rol", "") == "conductor":
            consulta = consulta.filter(
                Q(conductor__usuario=usuario) | Q(entregas__conductor__usuario=usuario)
            ).distinct()
        else:
            consulta = consulta.filter(Q(usuario=usuario) | Q(cliente__usuario=usuario))

    mensaje_lower = (mensaje or "").lower()
    if "pendiente" in mensaje_lower:
        consulta = consulta.filter(estado="pendiente")
    elif "en ruta" in mensaje_lower or "en camino" in mensaje_lower:
        consulta = consulta.filter(estado="en_ruta")
    elif "entregado" in mensaje_lower:
        consulta = consulta.filter(estado="entregado")
    elif "cancelado" in mensaje_lower:
        consulta = consulta.filter(estado="cancelado")
    elif "autorizado" in mensaje_lower or "despacho" in mensaje_lower:
        consulta = consulta.filter(estado__in=["autorizado_despacho", "vehiculo_asignado"])

    pedidos = list(consulta[:10])
    if not pedidos:
        return "No encontré pedidos que coincidan."
    return "Pedidos:\n" + "\n".join(
        f"- Pedido #{pedido.codigo_pedido}: {ESTADO_PEDIDO.get(pedido.estado, pedido.estado)} - ${_format_number(pedido.total)}"
        for pedido in pedidos
    )


def consultar_pagos_y_facturas(mensaje, usuario=None):
    from apps.pagos.models import Factura, Pago

    m = (mensaje or "").lower()
    es_admin = _es_admin(usuario)

    if "factura" in m:
        qs = Factura.objects.select_related("pedido", "cliente__usuario").order_by("-fecha_emision")
        if usuario and getattr(usuario, "is_authenticated", False) and not es_admin:
            qs = qs.filter(Q(cliente__usuario=usuario) | Q(pedido__usuario=usuario))
        if "pendiente" in m or "emitida" in m:
            qs = qs.filter(estado__in=["emitida", "parcial"])
        elif "pagada" in m:
            qs = qs.filter(estado="pagada")
        facturas = list(qs[:10])
        if not facturas:
            return "No encontré facturas registradas con ese criterio."
        return f"Facturas encontradas ({len(facturas)}):\n" + "\n".join(
            f"- {f.numero} (Pedido #{f.pedido.codigo_pedido if f.pedido_id else 'N/A'}): {f.get_estado_display()} — Total ${_format_number(f.total)}"
            for f in facturas
        )

    qs = Pago.objects.select_related("pedido").order_by("-fecha_registro")
    if usuario and getattr(usuario, "is_authenticated", False) and not es_admin:
        qs = qs.filter(Q(pedido__usuario=usuario) | Q(pedido__cliente__usuario=usuario))

    if "pendiente" in m:
        qs = qs.filter(estado=Pago.PENDIENTE)
    elif "aprobado" in m:
        qs = qs.filter(estado=Pago.APROBADO)
    elif "rechazado" in m:
        qs = qs.filter(estado=Pago.RECHAZADO)

    total = qs.count()
    pagos = list(qs[:8])
    if not pagos:
        return "No encontré pagos registrados con ese criterio."
    return f"Pagos ({total} en total, mostrando últimos {len(pagos)}):\n" + "\n".join(
        f"- Pedido #{p.pedido.codigo_pedido}: {p.get_metodo_display()} — {p.get_estado_display()} (${_format_number(p.monto)})"
        for p in pagos
    )


def consultar_logistica(mensaje, usuario=None):
    from apps.logistica.models import Entrega, Novedad, Vehiculo

    m = (mensaje or "").lower()
    es_admin = _es_admin(usuario)

    if any(k in m for k in ["novedad", "novedades", "incidente", "incidentes"]):
        qs = Novedad.objects.select_related("entrega__pedido", "reportado_por").order_by("-fecha_generada")
        if usuario and getattr(usuario, "is_authenticated", False) and not es_admin:
            qs = qs.filter(Q(reportado_por=usuario) | Q(entrega__conductor__usuario=usuario))
        if "abierta" in m:
            qs = qs.filter(estado="abierta")
        novedades = list(qs[:8])
        if not novedades:
            return "No hay novedades de entrega registradas con ese criterio."
        return f"Novedades registradas ({len(novedades)}):\n" + "\n".join(
            f"- Novedad #{n.id_novedad} (Pedido #{n.entrega.pedido.codigo_pedido}): {n.get_tipo_display()} — {n.get_estado_display()}"
            for n in novedades
        )

    if any(k in m for k in ["entrega", "entregas", "despacho", "despachos"]):
        qs = Entrega.objects.select_related("pedido", "vehiculo", "conductor__usuario").order_by("-id_entrega")
        if usuario and getattr(usuario, "is_authenticated", False) and not es_admin:
            if getattr(usuario, "rol", "") == "conductor":
                qs = qs.filter(conductor__usuario=usuario)
            else:
                qs = qs.filter(Q(pedido__usuario=usuario) | Q(pedido__cliente__usuario=usuario))
        if "en ruta" in m:
            qs = qs.filter(estado="en_ruta")
        elif "pendiente" in m:
            qs = qs.filter(estado="pendiente")
        elif "entregad" in m:
            qs = qs.filter(estado="entregado")
        entregas = list(qs[:8])
        if not entregas:
            return "No encontré entregas con ese criterio."
        return f"Entregas ({len(entregas)} recientes):\n" + "\n".join(
            f"- Entrega #{e.id_entrega} (Pedido #{e.pedido.codigo_pedido}): {e.estado_logistico_display}"
            + (f" — Vehículo {e.vehiculo.placa}" if e.vehiculo_id else "")
            for e in entregas
        )

    if any(k in m for k in ["vehiculo", "vehículo", "flota", "camion", "camión", "volqueta", "placa"]):
        if usuario and getattr(usuario, "is_authenticated", False) and not es_admin:
            if getattr(usuario, "rol", "") == "conductor":
                from apps.logistica.models import ConductorVehiculo
                asig = (
                    ConductorVehiculo.objects.filter(conductor__usuario=usuario, fecha_fin__isnull=True)
                    .select_related("vehiculo")
                    .first()
                )
                if asig:
                    v = asig.vehiculo
                    return f"Tu vehículo asignado es {v.placa} ({v.marca} {v.modelo}, {v.tipo_vehiculo}, capacidad {v.capacidad_carga} t, estado: {v.get_estado_display()})."
                return "Actualmente no tienes un vehículo asignado."
            return "La consulta detallada de flota es exclusiva de administradores y conductores."

        qs = Vehiculo.objects.all().order_by("placa")
        if "disponible" in m:
            qs = qs.filter(estado="disponible")
        elif "en ruta" in m:
            qs = qs.filter(estado="en_ruta")
        elif "mantenimiento" in m:
            qs = qs.filter(estado="mantenimiento")
        vehiculos = list(qs[:12])
        if not vehiculos:
            return "No hay vehículos que coincidan con ese filtro."
        return f"Vehículos ({qs.count()} en total):\n" + "\n".join(
            f"- {v.placa}: {v.marca} {v.modelo} ({v.tipo_vehiculo}, {v.capacidad_carga} t) — {v.get_estado_display()}"
            for v in vehiculos
        )
    return None


def consultar_compras_y_proveedores(mensaje, usuario=None):
    from apps.compras.models import Compra, Proveedor

    if usuario and getattr(usuario, "is_authenticated", False) and not _es_admin(usuario):
        return "La información de compras y proveedores es de acceso exclusivo para administradores."

    m = (mensaje or "").lower()
    if "proveedor" in m:
        provs = list(Proveedor.objects.all().order_by("nombre_empresa")[:12])
        if not provs:
            return "No hay proveedores registrados."
        return f"Proveedores registrados ({Proveedor.objects.count()}):\n" + "\n".join(
            f"- {p.nombre_empresa} (NIT: {p.nit}) — {p.ciudad or 'Sin ciudad'} | Contacto: {p.contacto_nombre or p.telefono}"
            for p in provs
        )

    compras = Compra.objects.select_related("proveedor").order_by("-fecha_compra")
    if "pendiente" in m:
        compras = compras.filter(estado="pendiente")
    elif "recibida" in m:
        compras = compras.filter(estado="recibida")
    total_monto = compras.aggregate(s=Sum("total_compra"))["s"] or 0
    lista = list(compras[:8])
    if not lista:
        return "No hay compras registradas con ese criterio."
    return (
        f"Compras ({compras.count()} en total — Inversión: ${_format_number(total_monto)}):\n"
        + "\n".join(
            f"- Compra #{c.pk} ({c.proveedor.nombre_empresa}): {c.estado} — ${_format_number(c.total_compra)}"
            for c in lista
        )
    )


def consultar_auditoria(mensaje, usuario=None):
    from apps.auditoria.models import Historial

    if usuario and getattr(usuario, "is_authenticated", False) and not _es_admin(usuario):
        return "El historial de auditoría solo puede ser consultado por administradores."

    logs = list(Historial.objects.select_related("usuario").order_by("-fecha")[:8])
    if not logs:
        return "No hay registros de auditoría todavía."
    return "Últimas acciones registradas en Auditoría:\n" + "\n".join(
        f"- [{h.accion.upper()}] {h.modulo or h.tabla or 'sistema'} por {h.usuario.username if h.usuario_id else 'sistema'}: {(h.descripcion or '')[:90]}"
        for h in logs
    )


def consultar_notificaciones_y_sugerencias(mensaje, usuario=None):
    m = (mensaje or "").lower()
    if "notificacion" in m or "notificación" in m or "notificaciones" in m:
        if not usuario or not getattr(usuario, "is_authenticated", False):
            return "Inicia sesión para consultar tus notificaciones."
        from apps.usuarios.models import Notificacion

        no_leidas = Notificacion.objects.filter(usuario=usuario, leida=False).order_by("-fecha_creacion")
        count = no_leidas.count()
        if count == 0:
            return "No tienes notificaciones sin leer. ¡Todo está al día!"
        top = list(no_leidas[:5])
        return f"Tienes {count} notificación(es) sin leer:\n" + "\n".join(
            f"- {n.titulo}: {n.mensaje[:90]}" for n in top
        )

    if "sugerencia" in m:
        if usuario and getattr(usuario, "is_authenticated", False) and not _es_admin(usuario):
            return "Puedes enviar una nueva sugerencia desde el Centro de Ayuda (/ayuda/) usando el botón «Enviar Sugerencia»."
        from apps.ayuda.models import SugerenciaRecomendacion

        total = SugerenciaRecomendacion.objects.count()
        nuevas = SugerenciaRecomendacion.objects.filter(estado="nuevo").count()
        return f"Sugerencias registradas: {total} en total ({nuevas} nuevas pendientes de revisión)."
    return None


def consultar_mi_perfil(usuario):
    if not usuario or not getattr(usuario, "is_authenticated", False):
        return "Inicia sesión para consultar los datos de tu perfil."
    nombre = f"{usuario.nombres} {usuario.apellidos}".strip() or usuario.username
    ultimo = usuario.last_login.strftime("%d/%m/%Y %H:%M") if usuario.last_login else "Sesión actual"
    return (
        f"Datos de tu perfil:\n"
        f"- Nombre: {nombre}\n"
        f"- Usuario: @{usuario.username}\n"
        f"- Rol: {getattr(usuario, 'rol', 'usuario').capitalize()}\n"
        f"- Correo: {usuario.email or 'No registrado'}\n"
        f"- Teléfono: {getattr(usuario, 'telefono', '') or 'No registrado'}\n"
        f"- Estado: {getattr(usuario, 'estado', 'activo').capitalize()}\n"
        f"- Última conexión: {ultimo}"
    )


def consultar_datos(mensaje, usuario=None):
    """Responde consultas verificables desde la BD antes de llamar al LLM."""
    try:
        mensaje_lower = (mensaje or "").lower()

        # 1. Pedido específico por número/código
        codigo = _extraer_codigo_pedido(mensaje)
        if re.search(r"pedido|orden", mensaje_lower) and codigo:
            respuesta = consultar_pedido(codigo, usuario=usuario)
            if respuesta:
                return respuesta

        # 2. Datos propios del usuario ("mis datos", "mi cuenta", "quién soy")
        if re.search(r"\b(quien soy|quién soy|mis datos|mi cuenta|mi correo|mi telefono|mi teléfono)\b", mensaje_lower):
            return consultar_mi_perfil(usuario)

        # 3. Notificaciones y sugerencias
        if re.search(r"notificaci[oó]n|notificaciones|cu[áa]ntas sugerencias|lista.*sugerencias", mensaje_lower):
            resp = consultar_notificaciones_y_sugerencias(mensaje, usuario)
            if resp:
                return resp

        # 4. Auditoría / historial reciente (consulta de datos)
        if re.search(r"(ultim[ao]s?|recientes?|ver|muestra|listar?).*(auditor[íi]a|acciones|bit[áa]cora|historial de actividad)", mensaje_lower):
            return consultar_auditoria(mensaje, usuario)

        # 5. Pagos y facturas (consulta de datos)
        if re.search(r"(cu[áa]ntos|cuales|cuáles|ver|listar?|mis|ultim[ao]s?|estado|pendientes?|aprobados?|rechazados?).*(pago|pagos|factura|facturas)|(pago|pagos|factura|facturas).*(pendientes?|aprobados?|rechazados?|pagadas?)", mensaje_lower):
            return consultar_pagos_y_facturas(mensaje, usuario)

        # 6. Logística: novedades, entregas y vehículos (consulta de datos)
        if re.search(r"(cu[áa]nt[ao]s|cuales|cuáles|ver|listar?|mis|ultim[ao]s?|disponibles?|en ruta|mantenimiento|abiertas?).*(novedad|novedades|entrega|entregas|veh[íi]culo|veh[íi]culos|flota|cami[oó]n)|(novedad|novedades|entrega|entregas|veh[íi]culo|veh[íi]culos).*(disponibles?|en ruta|mantenimiento|pendientes?|abiertas?)", mensaje_lower):
            resp = consultar_logistica(mensaje, usuario)
            if resp:
                return resp

        # 7. Compras y proveedores (consulta de datos)
        if re.search(r"(cu[áa]nt[ao]s|cuales|cuáles|ver|listar?|ultim[ao]s?|total|pendientes?|recibidas?).*(compra|compras|proveedor|proveedores)", mensaje_lower):
            return consultar_compras_y_proveedores(mensaje, usuario)

        # 8. Stock crítico / movimientos de inventario
        if re.search(r"stock bajo|stock cr[íi]tico|agotado|movimientos? de inventario|kardex", mensaje_lower):
            resp = consultar_stock_y_movimientos(mensaje, usuario)
            if resp:
                return resp

        # 9. Marcas, unidades de medida, tipos de material
        if re.search(r"(cuales|cuáles|qué|que|listar?|ver).*(marcas?|unidades? de medida|tipos? de material|categor[íi]as?)", mensaje_lower):
            resp = consultar_catalogo_marcas_unidades(mensaje)
            if resp:
                return resp

        # 10. Materiales / catálogo / precios
        if re.search(r"material|inventario|stock|cat[áa]logo|precio", mensaje_lower):
            return consultar_materiales(mensaje)

        # 11. Pedidos (lista general o por estado)
        if re.search(r"pedido|pendiente|mis pedidos", mensaje_lower):
            return consultar_pedidos_cliente(mensaje, usuario)
    except Exception:
        logger.exception("Error en la consulta ORM de IA")
    return None
