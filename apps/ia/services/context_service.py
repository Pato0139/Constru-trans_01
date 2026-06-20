import logging
from datetime import datetime
from django.core.cache import cache
from django.db.models import F, Sum

logger = logging.getLogger(__name__)

CONTEXT_CACHE_KEY = "ia_contexto_datos_v2"
CONTEXT_CACHE_TTL = 60


def obtener_contexto_datos(force_refresh=False, usuario=None):
    if not force_refresh and not usuario:
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
        from django.db.models import Count

        # --- DATOS GLOBALES (siempre los obtenemos para admin o anónimo) ---
        # Obtener vehículos asociados a cada conductor (todos los registros, estructurados)
        asignaciones_activas = ConductorVehiculo.objects.filter(fecha_fin__isnull=True).select_related("conductor__usuario", "vehiculo")
        total_conductores_con_vehiculo = asignaciones_activas.count()
        vehiculos_por_conductor_lista = []
        for asignacion in asignaciones_activas:
            nombre_conductor = f"{asignacion.conductor.usuario.nombres} {asignacion.conductor.usuario.apellidos}"
            vehiculos_por_conductor_lista.append({
                "nombre": nombre_conductor,
                "marca": asignacion.vehiculo.marca,
                "modelo": asignacion.vehiculo.modelo,
                "placa": asignacion.vehiculo.placa
            })

        # Obtener cliente con más pedidos
        top_cliente = None
        try:
            # Aggregate pedidos por cliente
            clientes_pedidos = PedidoGestion.objects.values('cliente').annotate(num_pedidos=Count('id')).order_by('-num_pedidos')
            if clientes_pedidos and clientes_pedidos[0]['cliente']:
                cliente_obj = Cliente.objects.select_related('usuario').filter(id=clientes_pedidos[0]['cliente']).first()
                if cliente_obj:
                    top_cliente = {
                        "nombre": f"{cliente_obj.usuario.nombres} {cliente_obj.usuario.apellidos}",
                        "num_pedidos": clientes_pedidos[0]['num_pedidos']
                    }
        except Exception:
            logger.exception("Error obteniendo cliente con más pedidos")

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
            "top_cliente": top_cliente,
            "generated_at": datetime.now().isoformat(),
        }

        # --- DATOS PERSONALIZADOS POR USUARIO ---
        if usuario and usuario.is_authenticated:
            rol_usuario = getattr(usuario, "rol", None)
            
            # DATOS PARA CLIENTES
            if rol_usuario == "cliente":
                try:
                    cliente_obj = Cliente.objects.filter(usuario=usuario).first()
                    if cliente_obj:
                        pedidos_cliente = PedidoGestion.objects.filter(cliente=cliente_obj)
                        data["mis_pedidos_totales"] = pedidos_cliente.count()
                        data["mis_pedidos_pendientes"] = pedidos_cliente.filter(estado="pendiente").count()
                        data["mis_pedidos_entregados"] = pedidos_cliente.filter(estado="entregado").count()
                        
                        facturas_cliente = Factura.objects.filter(cliente=cliente_obj)
                        data["mis_facturas_pendientes"] = facturas_cliente.filter(estado="pendiente").count()
                        data["mis_facturas_pagadas"] = facturas_cliente.filter(estado="pagada").count()
                except Exception:
                    logger.exception("Error obteniendo datos personalizados para cliente")
            
            # DATOS PARA CONDUCTORES
            elif rol_usuario == "conductor":
                try:
                    from apps.usuarios.models import Conductor
                    conductor_obj = Conductor.objects.filter(usuario=usuario).first()
                    if conductor_obj:
                        # Obtener sus entregas (asumiendo que hay una relación, usamos pedidos asignados a él por ahora)
                        pedidos_conductor = PedidoGestion.objects.filter(conductor=conductor_obj)
                        data["mis_entregas_pendientes"] = pedidos_conductor.filter(estado__in=["pendiente", "aprobado", "en_camino"]).count()
                        data["mis_entregas_completadas"] = pedidos_conductor.filter(estado="entregado").count()
                        
                        # Obtener su vehículo asignado
                        asignacion = ConductorVehiculo.objects.filter(conductor=conductor_obj, fecha_fin__isnull=True).select_related("vehiculo").first()
                        if asignacion:
                            data["mi_vehiculo"] = f"{asignacion.vehiculo.marca} {asignacion.vehiculo.modelo} (Placa: {asignacion.vehiculo.placa})"
                        else:
                            data["mi_vehiculo"] = "Sin vehículo asignado"
                except Exception:
                    logger.exception("Error obteniendo datos personalizados para conductor")
        
        # Cachear solo datos globales
        if not usuario:
            cache.set(CONTEXT_CACHE_KEY, data, CONTEXT_CACHE_TTL)
            
        return data

    except Exception:
        logger.exception("Error obteniendo contexto de datos")
        return {}
