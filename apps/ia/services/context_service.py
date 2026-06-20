import logging
from datetime import datetime
from django.core.cache import cache
from django.db.models import F, Sum

logger = logging.getLogger(__name__)

CONTEXT_CACHE_KEY = "ia_contexto_datos_v2"
CONTEXT_CACHE_TTL = 60


def obtener_contexto_datos(force_refresh=False):
    if not force_refresh:
        cached = cache.get(CONTEXT_CACHE_KEY)
        if cached:
            return cached

    try:
        from apps.usuarios.models import Usuario, MaterialConstruccion, Stock, Proveedor, Vehiculo, ConductorVehiculo
        from apps.clientes.models import Cliente
        from apps.gestion_pedidos.models import Pedido as PedidoGestion
        from apps.compras.models import Compra
        from apps.facturacion.models import Factura
        from apps.pagos.models import Pago

        # Obtener vehículos asociados a cada conductor (info resumida)
        asignaciones_activas = ConductorVehiculo.objects.filter(fecha_fin__isnull=True).select_related("conductor__usuario", "vehiculo")
        total_conductores_con_vehiculo = asignaciones_activas.count()
        vehiculos_por_conductor_lista = []
        for i, asignacion in enumerate(asignaciones_activas[:5], 1): # Solo los primeros 5
            nombre_conductor = f"{asignacion.conductor.usuario.nombres} {asignacion.conductor.usuario.apellidos}"
            vehiculo_info = f"{asignacion.vehiculo.marca} {asignacion.vehiculo.modelo} (Placa: {asignacion.vehiculo.placa})"
            vehiculos_por_conductor_lista.append(f"{nombre_conductor}: {vehiculo_info}")

        data = {
            "total_usuarios": Usuario.objects.count(),
            "usuarios_activos": Usuario.objects.filter(estado="activo").count(),
            "admin_count": Usuario.objects.filter(rol="admin").count(),
            "cliente_count": Usuario.objects.filter(rol="cliente").count(),
            "conductor_count": Usuario.objects.filter(rol="conductor").count(),
            "empleado_count": Usuario.objects.filter(rol="empleado").count(),

            "total_materiales": MaterialConstruccion.objects.count(),
            "total_stock": Stock.objects.aggregate(total=Sum("cantidad_actual"))["total"] or 0,
            "stock_bajo": Stock.objects.filter(cantidad_actual__lte=F("stock_minimo")).count(),

            "pedidos_totales": PedidoGestion.objects.count(),
            "pedidos_pendientes": PedidoGestion.objects.filter(estado="pendiente").count(),
            "pedidos_aprobados": PedidoGestion.objects.filter(estado="aprobado").count(),
            "pedidos_en_camino": PedidoGestion.objects.filter(estado="en_camino").count(),
            "pedidos_entregados": PedidoGestion.objects.filter(estado="entregado").count(),
            "pedidos_cancelados": PedidoGestion.objects.filter(estado="cancelado").count(),
            "total_ventas": PedidoGestion.objects.aggregate(total=Sum("total"))["total"] or 0,

            "compras_totales": Compra.objects.count(),
            "compras_pendientes": Compra.objects.filter(estado="pendiente").count(),
            "compras_recibidas": Compra.objects.filter(estado="recibida").count(),
            "total_compras": Compra.objects.aggregate(total=Sum("total_compra"))["total"] or 0,

            "facturas_totales": Factura.objects.count(),
            "facturas_pendientes": Factura.objects.filter(estado="pendiente").count(),
            "facturas_pagadas": Factura.objects.filter(estado="pagada").count(),
            "total_facturado": Factura.objects.aggregate(total=Sum("total"))["total"] or 0,

            "pagos_totales": Pago.objects.count(),
            "total_pagado": Pago.objects.aggregate(total=Sum("monto"))["total"] or 0,

            "proveedores_count": Proveedor.objects.count(),

            "vehiculos_count": Vehiculo.objects.count(),
            "vehiculos_disponibles": Vehiculo.objects.filter(estado="disponible").count(),
            "vehiculos_en_ruta": Vehiculo.objects.filter(estado="en_ruta").count(),
            "total_conductores_con_vehiculo": total_conductores_con_vehiculo,
            "vehiculos_por_conductor_lista": vehiculos_por_conductor_lista,

            "clientes_registrados": Cliente.objects.count(),
            "generated_at": datetime.now().isoformat(),
        }

        cache.set(CONTEXT_CACHE_KEY, data, CONTEXT_CACHE_TTL)
        return data

    except Exception:
        logger.exception("Error obteniendo contexto de datos")
        return {}
