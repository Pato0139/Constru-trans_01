import os
import sys
from datetime import date, timedelta
from decimal import Decimal

import django
from django.utils import timezone

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.base")
django.setup()

from django.contrib.admin.models import LogEntry
from django.db import connections, transaction

from apps.clientes.models import Cliente
from apps.compras.models import Compra, DetalleCompra
from apps.facturacion.models import Factura
from apps.historial.models import Historial
from apps.inventario.models import MovimientoInventario
from apps.ordenes.models import DetallePedido, Entrega, Pedido
from apps.pagos.models import Pago
from apps.reportes.models import HistorialReporte, Reporte
from apps.usuarios.models import (
    EPS,
    Catalogo,
    Conductor,
    ConductorVehiculo,
    MaterialConstruccion,
    MetodoPago,
    Notificacion,
    Proveedor,
    Stock,
    Usuario,
    Vehiculo,
)


def seed_database_instance(db_alias):
    """
    Pobla una base de datos específica (default o remota) con un set completo de datos
    consistente, respetando la integridad referencial.
    """
    print(f"\n---> Iniciando poblado en base de datos: [{db_alias}]...")

    # Desactivar restricciones de llaves foráneas temporalmente en Django y SQLite
    try:
        connections[db_alias].disable_constraint_checking()
        if connections[db_alias].vendor == "sqlite":
            with connections[db_alias].cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys = OFF;")
    except Exception:
        pass

    # Limpieza en orden inverso de dependencias en esta base de datos específica
    print(f"  [{db_alias}] Limpiando tablas existentes...")
    LogEntry.objects.using(db_alias).all().delete()
    HistorialReporte.objects.using(db_alias).all().delete()
    Reporte.objects.using(db_alias).all().delete()
    Historial.objects.using(db_alias).all().delete()
    Notificacion.objects.using(db_alias).all().delete()
    MovimientoInventario.objects.using(db_alias).all().delete()
    DetalleCompra.objects.using(db_alias).all().delete()
    Compra.objects.using(db_alias).all().delete()
    Pago.objects.using(db_alias).all().delete()
    Factura.objects.using(db_alias).all().delete()
    Entrega.objects.using(db_alias).all().delete()
    DetallePedido.objects.using(db_alias).all().delete()
    Pedido.objects.using(db_alias).all().delete()
    Stock.objects.using(db_alias).all().delete()
    MaterialConstruccion.objects.using(db_alias).all().delete()
    Catalogo.objects.using(db_alias).all().delete()
    Proveedor.objects.using(db_alias).all().delete()
    ConductorVehiculo.objects.using(db_alias).all().delete()
    Vehiculo.objects.using(db_alias).all().delete()
    Conductor.objects.using(db_alias).all().delete()
    EPS.objects.using(db_alias).all().delete()
    Cliente.objects.using(db_alias).all().delete()
    MetodoPago.objects.using(db_alias).all().delete()
    Usuario.objects.using(db_alias).all().delete()

    print(f"  [{db_alias}] Insertando nuevos registros...")

    # ==========================================
    # 1. USUARIOS (Al menos 15 registros de varios roles)
    # ==========================================
    usuarios = []

    # Admin solicitado
    admin_u = Usuario(
        username="admin@c.com",
        email="admin@c.com",
        nombres="Administrador",
        apellidos="General",
        documento="0000000000",
        tipo_documento="CC",
        rol="admin",
        estado="activo",
        is_staff=True,
        is_superuser=True,
    )
    admin_u.set_password("@dmin123")
    admin_u.save(using=db_alias)
    usuarios.append(admin_u)

    # Cliente solicitado
    client_u = Usuario(
        username="client@c.com",
        email="client@c.com",
        nombres="Cliente",
        apellidos="Frecuente",
        documento="0000000001",
        tipo_documento="CC",
        rol="cliente",
        estado="activo",
    )
    client_u.set_password("@dmin123")
    client_u.save(using=db_alias)
    usuarios.append(client_u)

    for i in range(2, 6):
        u = Usuario(
            username=f"cliente{i}@test.com",
            email=f"cliente{i}@test.com",
            nombres=f"Cliente Nombres {i}",
            apellidos=f"Apellidos {i}",
            documento=f"100000000{i}",
            tipo_documento="CC",
            rol="cliente",
            estado="activo",
        )
        u.set_password("pass1234")
        u.save(using=db_alias)
        usuarios.append(u)

    for i in range(6, 12):
        u = Usuario(
            username=f"conductor{i}@test.com",
            email=f"conductor{i}@test.com",
            nombres=f"Conductor Nombres {i}",
            apellidos=f"Apellidos {i}",
            documento=f"200000000{i}",
            tipo_documento="CC",
            rol="conductor",
            estado="activo",
        )
        u.set_password("pass1234")
        u.save(using=db_alias)
        usuarios.append(u)

    # ==========================================
    # 2. CLIENTES (10 perfiles de cliente)
    # ==========================================
    clientes = []
    usuarios_clientes = [u for u in usuarios if u.rol == "cliente"]
    for idx, u_cl in enumerate(usuarios_clientes):
        c, created = Cliente.objects.using(db_alias).get_or_create(usuario=u_cl)
        c.nombre_empresa = f"Empresa Constructora {idx+1} SAS"
        c.direccion_principal = f"Avenida Carrera 15 # {idx+10} - {idx+20}"
        c.tipo_cliente = "empresa" if idx % 2 == 0 else "persona"
        c.save(using=db_alias)
        clientes.append(c)

    while len(clientes) < 10:
        idx = len(clientes)
        u_temp = Usuario(
            username=f"cliente_extra{idx}@test.com",
            email=f"cliente_extra{idx}@test.com",
            nombres=f"Cliente Extra {idx}",
            apellidos="Extra",
            documento=f"10000990{idx}",
            tipo_documento="CC",
            rol="cliente",
            estado="activo",
        )
        u_temp.set_password("pass1234")
        u_temp.save(using=db_alias)

        c, created = Cliente.objects.using(db_alias).get_or_create(usuario=u_temp)
        c.nombre_empresa = f"Ferretería Extra {idx}"
        c.direccion_principal = f"Calle {idx*5} # {idx+2} - 10"
        c.tipo_cliente = "persona"
        c.save(using=db_alias)
        clientes.append(c)

    # ==========================================
    # 3. EPS (10 registros)
    # ==========================================
    eps_list = []
    eps_nombres = [
        "Sura",
        "Sanitas",
        "Compensar",
        "Salud Total",
        "Famisanar",
        "Coosalud",
        "Nueva EPS",
        "Aliansalud",
        "Mutual Ser",
        "Capresoca",
    ]
    for idx, nombre in enumerate(eps_nombres):
        ep = EPS.objects.using(db_alias).create(
            codigo_eps=f"EPS{idx+1:03d}",
            numero_seguro=f"SEG-998877{idx}",
            ciudad="Bogotá" if idx % 2 == 0 else "Medellín",
            direccion=f"Avenida 100 # {idx+1}-50",
            telefono=f"310888990{idx}",
            correo=f'contacto@{nombre.lower().replace(" ", "")}.com',
        )
        eps_list.append(ep)

    # ==========================================
    # 4. CONDUCTORES (10 registros)
    # ==========================================
    conductores = []
    usuarios_conductores = [u for u in usuarios if u.rol == "conductor"]
    for idx, u_cond in enumerate(usuarios_conductores):
        cond = Conductor.objects.using(db_alias).create(
            usuario=u_cond,
            numero_licencia=f"LIC-9988{idx+100}",
            categoria_licencia="C2",
            fecha_vencimiento_licencia=date.today() + timedelta(days=365),
            estado="activo",
            eps=eps_list[idx % len(eps_list)],
        )
        conductores.append(cond)

    while len(conductores) < 10:
        idx = len(conductores)
        u_temp = Usuario(
            username=f"conductor_extra{idx}@test.com",
            email=f"conductor_extra{idx}@test.com",
            nombres=f"Chofer Extra {idx}",
            apellidos="Extra",
            documento=f"20000990{idx}",
            tipo_documento="CC",
            rol="conductor",
            estado="activo",
        )
        u_temp.set_password("pass1234")
        u_temp.save(using=db_alias)

        cond = Conductor.objects.using(db_alias).create(
            usuario=u_temp,
            numero_licencia=f"LIC-9988{idx+200}",
            categoria_licencia="C3",
            fecha_vencimiento_licencia=date.today() + timedelta(days=730),
            estado="activo",
            eps=eps_list[idx % len(eps_list)],
        )
        conductores.append(cond)

    # ==========================================
    # 5. VEHICULOS (10 registros)
    # ==========================================
    vehiculos = []
    marcas = [
        "Toyota",
        "Chevrolet",
        "Ford",
        "Hino",
        "Kenworth",
        "JAC",
        "Foton",
        "Volvo",
        "Scania",
        "Mercedes",
    ]
    modelos = ["Hilux", "NQR", "F-150", "Dutro", "T800", "1040", "Aumark", "FH16", "R450", "Actros"]
    for idx in range(10):
        v = Vehiculo.objects.using(db_alias).create(
            placa=f"ABC{idx}23" if idx % 2 == 0 else f"XYZ{idx}89",
            marca=marcas[idx],
            modelo=modelos[idx],
            tipo_vehiculo="Volqueta"
            if idx % 3 == 0
            else ("Camión Estacas" if idx % 3 == 1 else "Tractomula"),
            capacidad_carga=float(5 + idx * 2),
            estado="disponible",
        )
        vehiculos.append(v)

    # ==========================================
    # 6. CONDUCTORVEHICULO (10 registros)
    # ==========================================
    for idx in range(10):
        ConductorVehiculo.objects.using(db_alias).create(
            conductor=conductores[idx], vehiculo=vehiculos[idx]
        )

    # ==========================================
    # 7. PROVEEDORES (10 registros)
    # ==========================================
    proveedores = []
    prov_nombres = [
        "Aceros Bogotá",
        "Cales y Arenas SAS",
        "Ladrillera Central",
        "Cementos Argos S.A.",
        "Hierros Occidente",
        "Tubos del Caribe",
        "Herramientas Pro",
        "Agregados del Norte",
        "Ladrillera del Sur",
        "Pinturas Global",
    ]
    for idx, nombre in enumerate(prov_nombres):
        p = Proveedor.objects.using(db_alias).create(
            nit=f"90012345{idx}-1",
            nombre_empresa=nombre,
            telefono=f"312777889{idx}",
            correo=f'contacto@{nombre.lower().replace(" ", "").replace(".","")}.com',
            descripcion=f"Proveedor oficial de materiales de la marca {nombre}.",
        )
        proveedores.append(p)

    # ==========================================
    # 7.5. CATALOGO (Tipos de Material)
    # ==========================================
    print(f"  [{db_alias}] Insertando tipos de material (Catalogo)...")
    tipos_cat = [
        ("CAT-CEM", "Cementos y Hormigón"),
        ("CAT-ARE", "Arenas y Grava"),
        ("CAT-MET", "Metales y Acero"),
        ("CAT-TUB", "Tuberías y PVC"),
        ("CAT-PIN", "Pinturas y Acabados"),
        ("CAT-GEN", "Materiales Generales"),
    ]
    catalogos_dict = {}
    for cod, nom in tipos_cat:
        cat = Catalogo.objects.using(db_alias).create(codigo_catalogo=cod, nombre_empresa=nom)
        catalogos_dict[cod] = cat

    # ==========================================
    # 8. MATERIALES DE CONSTRUCCION (10 registros)
    # ==========================================
    materiales = []
    mat_data = [
        ("Cemento Gris Bulto 50kg", "Bulto", 28500, "CAT-CEM"),
        ('Varilla Corrugada 1/2"', "Unidad", 35000, "CAT-MET"),
        ("Arena de Río (m3)", "m3", 85000, "CAT-ARE"),
        ("Grava 3/4 (m3)", "m3", 92000, "CAT-ARE"),
        ("Ladrillo Limpio Estructural", "Unidad", 1500, "CAT-GEN"),
        ("Bloque de Arcilla Nº 4", "Unidad", 950, "CAT-GEN"),
        ('Tubo PVC 1/2" Agua Potable', "Unidad", 18000, "CAT-TUB"),
        ("Pintura Vinilo Blanco Galón", "Galón", 65000, "CAT-PIN"),
        ("Yeso Agrícola Bulto 25kg", "Bulto", 14000, "CAT-GEN"),
        ("Alambre Negro Calibre 18 Kg", "Kg", 8500, "CAT-MET"),
    ]
    for m_nombre, m_um, m_precio, m_cat_code in mat_data:
        m = MaterialConstruccion.objects.using(db_alias).create(
            nombre=m_nombre,
            unidad_medida=m_um,
            precio=m_precio,
            catalogo=catalogos_dict[m_cat_code],
            descripcion=f"Material de construcción de tipo {m_nombre} para alta resistencia.",
        )
        materiales.append(m)

    # ==========================================
    # 9. STOCK (10 registros)
    # ==========================================
    for idx, mat in enumerate(materiales):
        Stock.objects.using(db_alias).create(
            material=mat,
            cantidad_actual=1000 + idx * 100,
            stock_minimo=100 + idx * 10,
            ubicacion=f"Pasillo {idx+1} - Bodega Principal",
        )

    # ==========================================
    # 10. METODOPAGO (10 registros)
    # ==========================================
    metodos_base = [
        ("EFE", "Efectivo"),
        ("TRA", "Transferencia Bancaria"),
        ("TAR", "Tarjeta de Crédito"),
        ("DEB", "Tarjeta de Débito"),
        ("NEQ", "Nequi"),
        ("DAV", "Daviplata"),
        ("PSE", "Pago Seguro Electrónico"),
        ("BOL", "Boleto Bancario"),
        ("CRE", "Crédito ConstruTrans"),
        ("CHE", "Cheque de Gerencia"),
    ]
    metodos_pago = []
    for cod, met in metodos_base:
        mp = MetodoPago.objects.using(db_alias).create(codigo_metodo_pago=cod, metodo=met)
        metodos_pago.append(mp)

    # ==========================================
    # 11. PEDIDOS (10 registros)
    # ==========================================
    pedidos = []
    for idx in range(10):
        c_temp = clientes[idx % len(clientes)]
        p = Pedido.objects.using(db_alias).create(
            usuario=c_temp.usuario,
            cliente=c_temp,
            direccion_origen="Bodega Central de ConstruTrans",
            direccion_destino=f"Dirección de Obra #{idx+1} - Calle {10+idx}",
            fecha_entrega_programada=timezone.now() + timedelta(days=2),
            estado="pendiente" if idx % 3 == 0 else ("en_ruta" if idx % 3 == 1 else "entregado"),
        )
        pedidos.append(p)

    # ==========================================
    # 12. DETALLEPEDIDO (10 registros)
    # ==========================================
    for idx, ped in enumerate(pedidos):
        mat_temp = materiales[idx % len(materiales)]
        DetallePedido.objects.using(db_alias).create(
            pedido=ped, material=mat_temp, cantidad=10 + idx, precio_unitario=mat_temp.precio
        )
        ped.calcular_total()

    # ==========================================
    # 13. ENTREGAS (10 registros)
    # ==========================================
    for idx, ped in enumerate(pedidos):
        Entrega.objects.using(db_alias).create(
            pedido=ped,
            conductor=conductores[idx % len(conductores)].usuario,
            vehiculo=vehiculos[idx % len(vehiculos)],
            direccion_entrega=ped.direccion_destino,
            estado="pendiente"
            if ped.estado == "pendiente"
            else ("en_ruta" if ped.estado == "en_ruta" else "entregado"),
            fecha_salida=timezone.now() if ped.estado != "pendiente" else None,
            fecha_entrega=timezone.now() + timedelta(hours=3)
            if ped.estado == "entregado"
            else None,
        )

    # ==========================================
    # 14. FACTURAS (10 registros)
    # ==========================================
    facturas = []
    for idx, ped in enumerate(pedidos):
        sub = ped.total
        iva = sub * Decimal("0.19")
        tot = sub + iva
        f = Factura.objects.using(db_alias).create(
            pedido=ped,
            cliente=ped.usuario,
            numero=f"FAC-2026-{idx+1000:04d}",
            subtotal=sub,
            iva=iva,
            total=tot,
            estado="pagada" if ped.estado == "entregado" else "pendiente",
        )
        facturas.append(f)

    # ==========================================
    # 15. PAGOS (10 registros)
    # ==========================================
    for idx, fac in enumerate(facturas):
        Pago.objects.using(db_alias).create(
            factura=fac,
            monto=fac.total if fac.estado == "pagada" else fac.total / 2,
            codigo_metodo_pago=metodos_pago[idx % len(metodos_pago)],
            referencia=f"REF-TX-000{idx}",
            registrado_por=admin_u,
        )

    # ==========================================
    # 16. COMPRAS (10 registros)
    # ==========================================
    compras = []
    for idx in range(10):
        c = Compra.objects.using(db_alias).create(
            proveedor=proveedores[idx % len(proveedores)],
            estado="recibida" if idx % 2 == 0 else "pendiente",
            usuario=admin_u,
            observaciones=f"Compra de reposición automatizada por stock mínimo. ID {idx}",
        )
        compras.append(c)

    # ==========================================
    # 17. DETALLECOMPRA (10 registros)
    # ==========================================
    for idx, comp in enumerate(compras):
        mat_temp = materiales[idx % len(materiales)]
        DetalleCompra.objects.using(db_alias).create(
            compra=comp,
            material=mat_temp,
            cantidad=100 + idx * 5,
            precio_unitario=mat_temp.precio * Decimal("0.8"),  # Descuento de proveedor
        )
        comp.calcular_total()

    # ==========================================
    # 18. MOVIMIENTOINVENTARIO (10 registros)
    # ==========================================
    for idx in range(10):
        MovimientoInventario.objects.using(db_alias).create(
            material=materiales[idx % len(materiales)],
            tipo_movimiento="entrada" if idx % 2 == 0 else "salida",
            cantidad=50 + idx * 10,
            observacion=f"Movimiento periódico registrado en lote de prueba {idx}",
            usuario=admin_u,
        )

    # ==========================================
    # 19. NOTIFICACIONES (10 registros)
    # ==========================================
    for idx in range(10):
        Notificacion.objects.using(db_alias).create(
            usuario=usuarios[idx % len(usuarios)],
            titulo=f"Notificación de Prueba #{idx}",
            tipo="info" if idx % 2 == 0 else "danger",
            mensaje=f"Estimado usuario, este es un mensaje automatizado de pruebas para depurar el sistema. ID {idx}",
            leida=idx % 3 == 0,
        )

    # ==========================================
    # 20. HISTORIAL DE AUDITORIA (10 registros)
    # ==========================================
    for idx in range(10):
        Historial.objects.using(db_alias).create(
            usuario=admin_u,
            accion="crear" if idx % 2 == 0 else "editar",
            modulo="Pedido" if idx % 2 == 0 else "MaterialConstruccion",
            elemento_id=str(idx + 1),
            descripcion=f"Registro de auditoría de prueba {idx}",
            ip_address="192.168.1.50",
        )

    # ==========================================
    # 21. REPORTES (10 registros)
    # ==========================================
    reportes = []
    tipos_reporte = ["inventario", "ventas", "compras", "entregas", "financiero"]
    for idx in range(10):
        tipo = tipos_reporte[idx % len(tipos_reporte)]
        rep = Reporte.objects.using(db_alias).create(
            numero_reporte=f"REP-{idx+1000}",
            tipo=tipo,
            estado="generado",
            descripcion=f"Reporte mensual de prueba de tipo {tipo} #{idx}",
            usuario=admin_u,
        )
        reportes.append(rep)

    # ==========================================
    # 22. HISTORIALREPORTES (10 registros)
    # ==========================================
    for idx in range(10):
        HistorialReporte.objects.using(db_alias).create(
            codigo_historia=f"HIST-{idx+2000}",
            reporte=reportes[idx % len(reportes)],
            descripcion=f"Exportación de reporte exitosa #{idx}",
        )

    print(
        f"  [ÉXITO] ¡Todas las 22 tablas en la base de datos [{db_alias}] fueron pobladas exitosamente!"
    )


def run_seed():
    """
    Función de ejecución principal. Bypass al router de base de datos multidispositivo
    forzando que ambas bases de datos se pueblen de manera autocontenida y consistente.
    """
    import core.routers
    import core.utils

    # Salvar estado original de conexión remota del router
    original_conexion = core.utils.conexion_remota_disponible

    # --- FASE 1: POBLADO BASE LOCAL (default - SQLite) ---
    # Forzar que el router crea que no hay conexión para que escriba todo localmente
    core.utils.conexion_remota_disponible = lambda: False
    core.routers.conexion_remota_disponible = lambda: False

    try:
        with transaction.atomic(using="default"):
            seed_database_instance("default")
    except Exception as e:
        print(f"\n[ERROR] Falla al poblar base de datos local [default]: {e}")

    # --- FASE 2: POBLADO BASE NUBE (remota - Neon PostgreSQL) ---
    # Si hay conexión a internet/nube, forzar que el router apunte todo a la nube para poblar remota
    if original_conexion():
        core.utils.conexion_remota_disponible = lambda: True
        core.routers.conexion_remota_disponible = lambda: True
        try:
            with transaction.atomic(using="remota"):
                seed_database_instance("remota")
        except Exception as e:
            import traceback

            print(f"\n[ERROR] Falla al poblar base de datos nube [remota]: {e}")
            traceback.print_exc()
    else:
        print("\n[INFO] Conexión remota no disponible. Saltando fase de poblado en la nube.")

    # Restaurar estado del router
    core.utils.conexion_remota_disponible = original_conexion
    core.routers.conexion_remota_disponible = original_conexion

    print("\n=======================================================")
    print("[TODO TERMINADO] Cuentas creadas para inicio de sesión inmediato:")
    print(
        "  -> ADMINISTRADOR:  Correo: admin@c.com  / Contraseña: @dmin123 (Documento: 0000000000)"
    )
    print(
        "  -> CLIENTE:        Correo: client@c.com / Contraseña: @dmin123 (Documento: 0000000001)"
    )
    print("=======================================================")


if __name__ == "__main__":
    run_seed()
