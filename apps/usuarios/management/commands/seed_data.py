# Comando seed: AUTH_USER_MODEL = usuarios.Usuario (NO usar django.contrib.auth.models.User)

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid5, NAMESPACE_URL
from django.db import transaction

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models.signals import post_save
from django.utils import timezone

from apps.catalogo.models import MaterialConstruccion, Stock
from apps.catalogo.models.movimientos import MovimientoInventario
from apps.clientes.models import Cliente, crear_perfil_cliente
from apps.compras.models import Proveedor, ProveedorMaterial, Compra, DetalleCompra
from apps.catalogo.services import KardexService
from apps.logistica.models import ConductorVehiculo, Entrega, Vehiculo
from apps.pedidos.models import DetallePedido, Pedido
from apps.pagos.models import Pago
from apps.usuarios.models import EPS, Conductor, Usuario
from config.routers import EnrutadorInventario
from config.utils import conexion_remota_disponible

DEFAULT_PASSWORD = "davit12345"
_router = EnrutadorInventario()


class Command(BaseCommand):
    help = "Llena la base de datos con datos de prueba"

    def _db_for(self, model):
        """Usa la misma BD que el router híbrido (remota si hay Neon, si no local)."""
        return _router.db_for_write(model, **{}) or "default"

    def _databases_to_seed(self):
        """Pobla local primero (default=SQLite) y, si hay conexión, también remota."""
        if "remota" in settings.DATABASES and conexion_remota_disponible():
            return ["default", "remota"]
        return ["default"]

    def _ensure_usuario(
        self, db_alias, username, email, rol, nombres, apellidos, documento, **extra
    ):
        """Crea o recupera un Usuario (AUTH_USER_MODEL = usuarios.Usuario)."""
        usuario, created = Usuario.objects.using(db_alias).get_or_create(
            username=username,
            defaults={
                "email": email,
                "nombres": nombres,
                "apellidos": apellidos,
                "documento": documento,
                "tipo_documento": "CC",
                "rol": rol,
                "estado": "activo",
                **extra,
            },
        )
        if created:
            usuario.set_password(DEFAULT_PASSWORD)
            usuario.save(using=db_alias)
        return usuario, created

    def _get_or_create_material(self, db_alias, m_data):
        """Evita MultipleObjectsReturned si hay duplicados por nombre."""
        qs = MaterialConstruccion.objects.using(db_alias).filter(nombre=m_data["nombre"])
        mat = qs.first()
        if mat:
            return mat, False

        # Get or create the UnidadMedida instance dynamically
        from apps.catalogo.models import UnidadMedida

        unidad_str = m_data["unidad_medida"]
        abreviaturas = {
            "Bulto": "Bto",
            "Unidad": "Und",
            "m3": "m3",
            "Kg": "kg",
            "Galón": "Gl",
            "Galn": "Gl",
        }
        abrev = abreviaturas.get(unidad_str, unidad_str[:10])
        codigo = unidad_str.upper()[:10]

        unidades = UnidadMedida.objects.using(db_alias)
        unidad_obj = unidades.filter(codigo=codigo).first()
        if unidad_obj is None:
            unidad_obj = unidades.filter(nombre=unidad_str).first()
        if unidad_obj is None:
            unidad_obj = unidades.create(
                codigo=codigo,
                nombre=unidad_str,
                abreviatura=abrev,
                activa=True,
            )

        m_data_copy = m_data.copy()
        m_data_copy["unidad_medida"] = unidad_obj

        mat = MaterialConstruccion.objects.using(db_alias).create(**m_data_copy)
        return mat, True

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-pedidos",
            action="store_true",
            help="Crea pedidos de demo aunque el cliente ya tenga pedidos",
        )
        parser.add_argument(
            "--database",
            choices=tuple(settings.DATABASES),
            help="Limita la carga a una base de datos específica.",
        )

    def _seed_database(self, db_alias, force_pedidos=False):
        self.stdout.write(self.style.NOTICE(f"\n--- Poblando base de datos: {db_alias} ---"))

        # 0. Superusuario / administrador
        admin_user, created = self._ensure_usuario(
            db_alias,
            username="Edward_Fonseca",
            email="edwardf5432@gmail.com",
            rol="admin",
            nombres="Edward",
            apellidos="Fonseca",
            documento="10101010",
            is_staff=True,
            is_superuser=True,
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Administrador Edward_Fonseca creado."))

        # 1. EPS (requerida para conductores)
        eps, _ = EPS.objects.using(db_alias).get_or_create(
            codigo_eps="EPS001",
            defaults={
                "numero_seguro": "123456789",
                "ciudad": "Bogota",
                "direccion": "Calle 100 # 10-10",
                "telefono": "3101234567",
                "correo": "contacto@eps.com",
            },
        )

        # 2. Proveedores
        proveedores_data = [
            {
                "nombre_empresa": "Aceros de Colombia S.A.",
                "nit": "900123456",
                "telefono": "3105556677",
                "correo": "ventas@aceroscol.com",
                "descripcion": "Proveedor de materiales de acero",
            },
            {
                "nombre_empresa": "Cales y Arenas del Sur",
                "nit": "800987654",
                "telefono": "3208889900",
                "correo": "contacto@calessur.com",
                "descripcion": "Proveedor de arenas y gravas",
            },
        ]

        ciudades_demo = ["Tunja", "Duitama", "Sogamoso", "Paipa"]
        for i, nombre in enumerate(["Cementos del Altiplano", "Ladrillera Boyacá", "Ferreaceros Central", "Agregados del Norte", "Maderas Andinas", "Pinturas del Valle", "Tuberías Oriente", "Construinsumos Paipa"], 1):
            proveedores_data.append({"nombre_empresa": nombre, "nit": f"990100{i:03d}", "telefono": f"310800{i:04d}", "correo": f"proveedor{i}@demo.example", "direccion": f"Calle {i + 10} # 12-30", "ciudad": ciudades_demo[i % 4], "descripcion": "Proveedor de demostración"})
        proveedores_demo = []
        for p_data in proveedores_data:
            prov, created = Proveedor.objects.using(db_alias).get_or_create(
                nit=p_data["nit"],
                defaults=p_data,
            )
            proveedores_demo.append(prov)
            if created:
                self.stdout.write(f"Proveedor creado: {prov.nombre_empresa}")

        # 3. Materiales y stock
        materiales_data = [
            {
                "nombre": "Cemento Gris Argos 50kg",
                "unidad_medida": "Bulto",
                "precio_referencia": 28500,
                "descripcion": "Bulto de cemento gris para construccion general",
            },
            {
                "nombre": 'Varilla Corrugada 1/2"',
                "unidad_medida": "Unidad",
                "precio_referencia": 35000,
                "descripcion": "Varilla de acero estructural 6 metros",
            },
            {
                "nombre": "Arena de Rio (m3)",
                "unidad_medida": "m3",
                "precio_referencia": 85000,
                "descripcion": "Arena fina para acabados",
            },
            {
                "nombre": "Grava 3/4 (m3)",
                "unidad_medida": "m3",
                "precio_referencia": 92000,
                "descripcion": "Grava triturada para concreto",
            },
            {
                "nombre": "Ladrillo Estructural",
                "unidad_medida": "Unidad",
                "precio_referencia": 1200,
                "descripcion": "Ladrillo de arcilla cocida",
            },
        ]

        for nombre, unidad, precio in [
            ("Ladrillo común", "Unidad", 900), ("Bloque de concreto", "Unidad", 3500),
            ("Cemento blanco 25kg", "Bulto", 48000), ("Mortero listo 40kg", "Bulto", 22000),
            ("Cal hidratada 25kg", "Bulto", 18000), ("Arena lavada", "m3", 95000),
            ("Piedra triturada", "m3", 110000), ("Malla electrosoldada", "Unidad", 85000),
            ("Alambre recocido", "Kg", 7500), ("Clavos para madera", "Kg", 9000),
            ("Tubo PVC sanitario", "Unidad", 38000), ("Codo PVC sanitario", "Unidad", 6500),
            ("Tabla de formaleta", "Unidad", 32000), ("Pintura blanca interior", "Galón", 65000),
            ("Impermeabilizante", "Galón", 78000)]:
            materiales_data.append({"nombre": nombre, "unidad_medida": unidad, "precio_referencia": precio, "descripcion": "Material de demostración para construcción"})

        mats = []
        for m_data in materiales_data:
            mat, created = self._get_or_create_material(db_alias, m_data)
            mats.append(mat)

            stock, _ = Stock.objects.using(db_alias).get_or_create(
                material=mat,
                defaults={
                    "cantidad_actual": 1000,
                    "stock_minimo": 100,
                    "ubicacion": "Bodega Principal",
                },
            )
            self.stdout.write(f"Material: {mat.nombre} - Stock: {stock.cantidad_actual}")

        # 4. Conductores y vehículos
        conductores_data = [
            {
                "username": "carlos_chofer",
                "email": "carlos@constru.com",
                "nombres": "Carlos",
                "apellidos": "Mendoza",
                "doc": "778899",
                "placa": "TRX-101",
                "marca": "Toyota",
                "modelo": "Hilux",
                "tipo": "Camion 5 Ton",
                "capacidad": 5.0,
            },
            {
                "username": "pedro_trans",
                "email": "pedro@constru.com",
                "nombres": "Pedro",
                "apellidos": "Salas",
                "doc": "554433",
                "placa": "KLM-202",
                "marca": "Chevrolet",
                "modelo": "Silverado",
                "tipo": "Bolqueta 10 Ton",
                "capacidad": 10.0,
            },
            {
                "username": "luis_driver",
                "email": "luis@constru.com",
                "nombres": "Luis",
                "apellidos": "Garcia",
                "doc": "998877",
                "placa": "ABC-123",
                "marca": "Ford",
                "modelo": "F-150",
                "tipo": "Camion 3 Ton",
                "capacidad": 3.0,
            },
        ]

        for i, (nombre, apellido) in enumerate([("Jorge", "Ramírez"), ("Diego", "Moreno"), ("Ana", "Castro"), ("Felipe", "Rojas"), ("Marta", "López"), ("Camilo", "Díaz"), ("Oscar", "Vargas")], 1):
            conductores_data.append({"username": f"demo_conductor_{i:02d}", "email": f"conductor{i}@demo.example", "nombres": nombre, "apellidos": apellido, "doc": f"990200{i:03d}", "placa": f"DMT{100+i}", "marca": ["Chevrolet", "Hino", "Isuzu"][i % 3], "modelo": str(2020 + i % 5), "tipo": "Camión" if i % 2 else "Volqueta", "capacidad": [5, 10, 15][i % 3]})
        conductores_creados = []
        vehiculos_creados = []
        for c_data in conductores_data:
            p_cond, created = self._ensure_usuario(
                db_alias,
                username=c_data["username"],
                email=c_data["email"],
                rol="conductor",
                nombres=c_data["nombres"],
                apellidos=c_data["apellidos"],
                documento=c_data["doc"],
            )
            if created:
                self.stdout.write(f"Conductor usuario creado: {p_cond.username}")

            cond_profile, _ = Conductor.ensure_for_user(
                p_cond,
                using=db_alias,
                defaults={
                    "numero_licencia": f"LIC-{c_data['doc']}",
                    "categoria_licencia": "C2",
                    "fecha_vencimiento_licencia": date.today() + timedelta(days=365),
                    "estado": "activo",
                    "eps": eps,
                },
            )

            cond_profile.usuario = p_cond
            vehiculo, vehiculo_creado = Vehiculo.objects.using(db_alias).get_or_create(
                placa=c_data["placa"],
                defaults={
                    "marca": c_data["marca"],
                    "modelo": c_data["modelo"],
                    "tipo_vehiculo": c_data["tipo"],
                    "capacidad_carga": c_data["capacidad"],
                    "estado": "disponible",
                },
            )
            vehiculos_creados.append(vehiculo)

            if vehiculo_creado:
                ConductorVehiculo.objects.using(db_alias).create(conductor=cond_profile, vehiculo=vehiculo)

            conductores_creados.append(cond_profile)
            self.stdout.write(f"Conductor {p_cond.nombres} y Vehiculo {c_data['placa']} listos.")

        # 5. Clientes y pedidos
        clientes_data = [
            {
                "username": "constructora_alfa",
                "email": "proyectos@alfa.com",
                "nombres": "Ing. Roberto",
                "apellidos": "Torres",
                "doc": "112233",
                "empresa": "Constructora Alfa SAS",
            },
            {
                "username": "ferreteria_central",
                "email": "compras@central.com",
                "nombres": "Lucia",
                "apellidos": "Perez",
                "doc": "445566",
                "empresa": "Ferreteria Central",
            },
            {
                "username": "obra_norte",
                "email": "obra@norte.com",
                "nombres": "Andres",
                "apellidos": "Rodriguez",
                "doc": "776655",
                "empresa": "Obra Norte Ltda",
            },
        ]

        for i in range(1, 18):
            clientes_data.append({"username": f"demo_cliente_{i:02d}", "email": f"cliente{i}@demo.example", "nombres": ["Laura", "Miguel", "Sandra", "Daniel", "Paula"][i % 5], "apellidos": ["Gómez", "Martínez", "Sánchez", "Pérez"][i % 4], "doc": f"990300{i:03d}", "empresa": f"Constructora Demo {i:02d}"})
        for cliente_indice, cl_data in enumerate(clientes_data):
            p_cl, created = self._ensure_usuario(
                db_alias,
                username=cl_data["username"],
                email=cl_data["email"],
                rol="cliente",
                nombres=cl_data["nombres"],
                apellidos=cl_data["apellidos"],
                documento=cl_data["doc"],
            )

            cliente_perfil, _ = Cliente.ensure_for_user(
                p_cl,
                using=db_alias,
                defaults={
                    "nombre_empresa": cl_data["empresa"],
                    "direccion": "Av Siempre Viva 123",
                    "tipo_cliente": "empresa",
                },
            )
            if not force_pedidos and Pedido.objects.using(db_alias).filter(usuario=p_cl).exists():
                for pedido_existente in Pedido.objects.using(db_alias).filter(usuario=p_cl):
                    estado_pago = (
                        Pago.APROBADO if pedido_existente.estado != "pendiente" else Pago.PENDIENTE
                    )
                    Pago.objects.using(db_alias).get_or_create(
                        pedido=pedido_existente,
                        defaults={
                            "metodo": Pago.METODO_CONTRAENTREGA,
                            "monto": pedido_existente.total,
                            "estado": estado_pago,
                            "observaciones": (
                                "Pedido de demostración contraentrega; no requiere comprobante."
                            ),
                        },
                    )
                self.stdout.write(
                    f"Cliente {cl_data['empresa']}: ya tiene pedidos; se verificaron sus pagos demo "
                    "contraentrega (use --force-pedidos para duplicar pedidos)."
                )
                continue

            estados_pedido = ["pendiente", "en_ruta", "entregado"]
            for idx, estado_p in enumerate(estados_pedido):
                pedido = Pedido.objects.using(db_alias).create(
                    usuario=p_cl,
                    cliente=cliente_perfil,
                    direccion_destino=f"Tunja — Obra {cl_data['empresa']} - Calle {100 + idx}",
                    estado=estado_p,
                )

                for mat in [mats[(cliente_indice * 3 + j) % len(mats)] for j in range(3)]:
                    cantidad = 20 + (idx * 10)
                    DetallePedido.objects.using(db_alias).create(
                        pedido=pedido,
                        material=mat,
                        cantidad=cantidad,
                        precio_unitario=mat.precio_referencia,
                    )

                pedido.calcular_total(using=db_alias)

                Pago.objects.using(db_alias).get_or_create(
                    pedido=pedido,
                    defaults={
                        "metodo": Pago.METODO_CONTRAENTREGA,
                        "monto": pedido.total,
                        "estado": Pago.APROBADO if estado_p != "pendiente" else Pago.PENDIENTE,
                        "observaciones": (
                            "Pedido de demostración contraentrega; no requiere comprobante."
                        ),
                    },
                )

                if estado_p != "pendiente" and conductores_creados and vehiculos_creados:
                    conductor_idx = cliente_indice % len(conductores_creados)
                    entrega = Entrega.objects.using(db_alias).create(
                        pedido=pedido,
                        conductor=conductores_creados[conductor_idx],
                        vehiculo=vehiculos_creados[conductor_idx],
                        direccion_entrega=pedido.direccion_destino,
                        estado="en_ruta" if estado_p == "en_ruta" else "entregado",
                        fecha_salida=timezone.now(),
                    )
                    if estado_p == "entregado":
                        entrega.fecha_entrega = timezone.now()
                        entrega.save(using=db_alias)

                self.stdout.write(
                    f"Cliente {cl_data['empresa']} - Pedido #{pedido.codigo_pedido} ({estado_p}) creado."
                )

        # 6. Movimientos de inventario
        self.stdout.write("\nGenerando movimientos de inventario...")
        for mat in mats:
            movimiento_existente = MovimientoInventario.objects.using(db_alias).filter(
                material=mat,
                tipo_movimiento="entrada",
                cantidad=1000,
                observacion="Carga inicial de inventario - Seeding",
            ).exists()
            if not movimiento_existente:
                MovimientoInventario.objects.using(db_alias).create(
                    material=mat,
                    tipo_movimiento="entrada",
                    cantidad=1000,
                    observacion="Carga inicial de inventario - Seeding",
                    usuario=admin_user,
                )
                self.stdout.write(f"Movimiento de entrada creado para: {mat.nombre}")

        # Entradas históricas identificadas con claves estables: repetir no suma stock.
        for i, proveedor in enumerate(proveedores_demo):
            asociados = [mats[(i * 2 + j) % len(mats)] for j in range(6)]
            for material in asociados:
                ProveedorMaterial.objects.using(db_alias).get_or_create(
                    proveedor=proveedor, material=material,
                    defaults={"precio_actual": (material.precio_referencia * Decimal("0.75")).quantize(Decimal("0.01")), "activo": True},
                )
            for lote in range(3):
                clave = uuid5(NAMESPACE_URL, f"construtrans/demo/entrada/{proveedor.nit}/{lote}")
                if Compra.objects.using(db_alias).filter(clave_idempotencia=clave).exists():
                    continue
                compra = Compra.objects.using(db_alias).create(
                    proveedor=proveedor, usuario=admin_user, estado="recibida",
                    clave_idempotencia=clave, numero_factura=f"DEMO-{i+1:02d}-{lote+1:02d}",
                    fecha_compra=timezone.now()-timedelta(days=30-i-lote*3), observaciones="Entrada de demostración",
                )
                for material in asociados[lote:lote+3]:
                    detalle = DetalleCompra.objects.using(db_alias).create(
                        compra=compra, material=material, cantidad=100 + lote*50,
                        precio_unitario=(material.precio_referencia * Decimal("0.75")).quantize(Decimal("0.01")),
                        precio_venta_unitario=material.precio_referencia,
                    )
                    KardexService.registrar_movimiento(material_id=material.pk, tipo="entrada", cantidad=detalle.cantidad, usuario=admin_user, compra_id=compra.pk, observacion="Recepción de demostración", using=db_alias)
        self.stdout.write(self.style.SUCCESS("\nDatos de prueba generados exitosamente!"))
        self.stdout.write("\nCredenciales de acceso:")
        self.stdout.write(f"- Admin: Edward_Fonseca / {DEFAULT_PASSWORD}")
        self.stdout.write(
            f"- Clientes: constructora_alfa, ferreteria_central, obra_norte / {DEFAULT_PASSWORD}"
        )
        self.stdout.write(
            f"- Conductores: carlos_chofer, pedro_trans, luis_driver / {DEFAULT_PASSWORD}"
        )

    def handle(self, *args, **options):
        force_pedidos = options.get("force_pedidos", False)
        self.stdout.write("Iniciando creacion de datos de prueba completos...")
        # Evitar que el signal cree Cliente en otra BD durante el seed
        post_save.disconnect(crear_perfil_cliente, sender=Usuario)
        try:
            db_aliases = [options["database"]] if options.get("database") else self._databases_to_seed()
            for db_alias in db_aliases:
                with transaction.atomic(using=db_alias):
                    self._seed_database(db_alias, force_pedidos=force_pedidos)
        finally:
            post_save.connect(crear_perfil_cliente, sender=Usuario)

        self.stdout.write(
            self.style.SUCCESS("\nProceso de seed finalizado en todas las bases configuradas.")
        )
