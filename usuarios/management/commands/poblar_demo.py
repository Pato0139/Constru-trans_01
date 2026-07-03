import random
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from usuarios.models import (
    Usuario,
    EPS,
    Conductor,
    Vehiculo,
    Catalogo,
    Proveedor,
    UnidadMedida,
    MaterialConstruccion,
    Stock,
    MetodoPago,
    Notificacion,
)
from clientes.models import Cliente
from compras.models import Compra, DetalleCompra
from gestion_pedidos.models import SolicitudPedido, DetalleSolicitudPedido
from ordenes.models import Pedido, DetallePedido, Entrega
from facturacion.models import Factura
from pagos.models import Pago
from reportes.models import Reporte, HistorialReporte


PASSWORD_DEMO = "Demo12345*"


class Command(BaseCommand):
    help = "Puebla automáticamente la base de datos con datos demo."

    def add_arguments(self, parser):
        parser.add_argument("--admins", type=int, default=2)
        parser.add_argument("--clientes", type=int, default=12)
        parser.add_argument("--conductores", type=int, default=6)
        parser.add_argument("--empleados", type=int, default=4)
        parser.add_argument("--compras", type=int, default=8)
        parser.add_argument("--solicitudes", type=int, default=8)
        parser.add_argument("--pedidos", type=int, default=10)

    def handle(self, *args, **options):
        with transaction.atomic():
            admins = self.crear_usuarios_admin(options["admins"])
            clientes = self.crear_clientes(options["clientes"])
            conductores = self.crear_conductores(options["conductores"])
            empleados = self.crear_empleados(options["empleados"])

            eps_list = self.crear_eps()
            vehiculos = self.crear_vehiculos()
            self.asignar_vehiculos(conductores, vehiculos)

            catalogos = self.crear_catalogos()
            unidades = self.crear_unidades()
            proveedores = self.crear_proveedores()
            materiales = self.crear_materiales(catalogos, unidades)
            self.crear_stock(materiales)
            metodos = self.crear_metodos_pago()

            self.crear_compras(options["compras"], proveedores, materiales, admins + empleados)
            self.crear_solicitudes(options["solicitudes"], clientes, materiales)
            pedidos = self.crear_pedidos(options["pedidos"], clientes, conductores, materiales)
            self.crear_facturas_y_pagos(pedidos, metodos, admins + empleados)
            self.crear_reportes(admins + empleados)
            self.crear_notificaciones(clientes, conductores, admins + empleados)

        self.stdout.write(self.style.SUCCESS("✅ Base de datos poblada correctamente."))

    # -----------------------------
    # Helpers
    # -----------------------------
    def nombre_random(self):
        nombres = [
            "Juan", "Pedro", "Ana", "Luisa", "Carlos", "María", "Camilo", "Laura",
            "Andrés", "Sofía", "Mateo", "Valentina", "Daniel", "Paula", "Iván", "Michell"
        ]
        apellidos = [
            "Gómez", "Pérez", "Rodríguez", "Martínez", "Sánchez", "Ramírez",
            "Torres", "López", "Castro", "Vargas", "Rojas", "Díaz"
        ]
        return random.choice(nombres), random.choice(apellidos)

    def documento_random(self, base=1000000000):
        return str(base + random.randint(1, 999999))

    def telefono_random(self):
        return "3" + "".join(str(random.randint(0, 9)) for _ in range(9))

    def email_from_username(self, username):
        return f"{username}@demo.com"

    def crear_usuario_base(self, idx, rol, is_staff=False, is_superuser=False):
        nombre, apellido = self.nombre_random()
        username = f"{rol}_{idx}"
        user, created = Usuario.objects.get_or_create(
            username=username,
            defaults={
                "email": self.email_from_username(username),
                "nombres": nombre,
                "apellidos": apellido,
                "telefono": self.telefono_random(),
                "documento": self.documento_random(base=1000000000 + idx * 1000),
                "rol": rol,
                "tipo_documento": "CC",
                "estado": "activo",
                "is_staff": is_staff,
                "is_superuser": is_superuser,
            },
        )
        if created:
            user.set_password(PASSWORD_DEMO)
            user.save()
        return user

    # -----------------------------
    # Usuarios
    # -----------------------------
    def crear_usuarios_admin(self, cantidad):
        admins = []
        for i in range(1, cantidad + 1):
            admins.append(
                self.crear_usuario_base(
                    idx=i,
                    rol="admin",
                    is_staff=True,
                    is_superuser=False,
                )
            )
        return admins

    def crear_clientes(self, cantidad):
        clientes = []
        for i in range(1, cantidad + 1):
            user = self.crear_usuario_base(idx=i, rol="cliente")
            perfil, _ = Cliente.objects.get_or_create(
                usuario=user,
                defaults={
                    "direccion_principal": f"Calle {i} # {10+i}-{20+i}",
                    "tipo_cliente": random.choice(["persona", "empresa"]),
                    "nombre_empresa": f"Cliente Empresa {i}" if i % 3 == 0 else "",
                    "nit": str(900000000 + i) if i % 3 == 0 else "",
                    "contacto_alternativo": f"Contacto {i}",
                    "observaciones": "Cliente generado automáticamente",
                },
            )
            clientes.append(perfil)
        return clientes

    def crear_eps(self):
        data = [
            ("EPS001", "Seguros Bolívar", "Bogotá"),
            ("EPS002", "Sanitas", "Medellín"),
            ("EPS003", "Sura", "Cali"),
            ("EPS004", "Nueva EPS", "Barranquilla"),
        ]
        eps_creadas = []
        for codigo, nombre, ciudad in data:
            eps, _ = EPS.objects.get_or_create(
                codigo_eps=codigo,
                defaults={
                    "numero_seguro": f"POL-{codigo}",
                    "ciudad": ciudad,
                    "direccion": f"Oficina principal {ciudad}",
                    "telefono": self.telefono_random(),
                    "correo": f"{nombre.lower().replace(' ', '')}@eps.com",
                },
            )
            eps_creadas.append(eps)
        return eps_creadas

    def crear_conductores(self, cantidad):
        eps_list = list(EPS.objects.all())
        if not eps_list:
            eps_list = self.crear_eps()

        conductores = []
        for i in range(1, cantidad + 1):
            user = self.crear_usuario_base(idx=i, rol="conductor")
            conductor, _ = Conductor.objects.get_or_create(
                usuario=user,
                defaults={
                    "numero_licencia": f"LIC-{10000+i}",
                    "categoria_licencia": random.choice(["B1", "C1", "C2"]),
                    "fecha_vencimiento_licencia": timezone.now().date() + timedelta(days=365 * 2),
                    "telefono_empresarial": self.telefono_random(),
                    "estado": "activo",
                    "fecha_ingreso": timezone.now().date() - timedelta(days=random.randint(30, 900)),
                    "eps": random.choice(eps_list),
                },
            )
            conductores.append(conductor)
        return conductores

    def crear_empleados(self, cantidad):
        empleados = []
        for i in range(1, cantidad + 1):
            empleados.append(self.crear_usuario_base(idx=i, rol="empleado"))
        return empleados

    # -----------------------------
    # Catálogos / inventario
    # -----------------------------
    def crear_vehiculos(self):
        marcas = [
            ("ABC101", "Chevrolet", "NHR", "Camión", Decimal("3500.00")),
            ("ABC102", "JAC", "1040", "Camión", Decimal("4000.00")),
            ("ABC103", "Mazda", "BT50", "Pickup", Decimal("1200.00")),
            ("ABC104", "Ford", "F150", "Pickup", Decimal("1400.00")),
            ("ABC105", "Hino", "300", "Camión", Decimal("5000.00")),
            ("ABC106", "Renault", "Kangoo", "Furgón", Decimal("800.00")),
        ]
        vehiculos = []
        for placa, marca, modelo, tipo, capacidad in marcas:
            v, _ = Vehiculo.objects.get_or_create(
                placa=placa,
                defaults={
                    "marca": marca,
                    "modelo": modelo,
                    "tipo_vehiculo": tipo,
                    "capacidad_carga": capacidad,
                    "estado": "disponible",
                },
            )
            vehiculos.append(v)
        return vehiculos

    def asignar_vehiculos(self, conductores, vehiculos):
        for conductor, vehiculo in zip(conductores, vehiculos):
            if conductor.vehiculo_actual != vehiculo:
                conductor.asignar_vehiculo(vehiculo)

    def crear_catalogos(self):
        nombres = [
            ("CAT001", "Constru-Trans"),
            ("CAT002", "FerreMateriales"),
            ("CAT003", "Acabados Premium"),
        ]
        catalogos = []
        for codigo, nombre in nombres:
            c, _ = Catalogo.objects.get_or_create(
                codigo_catalogo=codigo,
                defaults={"nombre_empresa": nombre},
            )
            catalogos.append(c)
        return catalogos

    def crear_unidades(self):
        data = [
            ("UND", "Unidad", "und", "Unidad individual", 1),
            ("BUL", "Bulto", "bul", "Bulto", 2),
            ("KG", "Kilogramo", "kg", "Peso", 3),
            ("M3", "Metro cúbico", "m3", "Volumen", 4),
            ("M2", "Metro cuadrado", "m2", "Área", 5),
        ]
        unidades = []
        for codigo, nombre, abrev, desc, orden in data:
            u, _ = UnidadMedida.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "abreviatura": abrev,
                    "descripcion": desc,
                    "activa": True,
                    "orden": orden,
                },
            )
            unidades.append(u)
        return unidades

    def crear_proveedores(self):
        data = [
            ("Cemex Colombia", "900100001"),
            ("Argos", "900100002"),
            ("Corona", "900100003"),
            ("Pintuco", "900100004"),
            ("Aceros SAS", "900100005"),
        ]
        proveedores = []
        for i, (nombre, nit) in enumerate(data, start=1):
            p, _ = Proveedor.objects.get_or_create(
                nit=nit,
                defaults={
                    "nombre_empresa": nombre,
                    "telefono": self.telefono_random(),
                    "correo": f"contacto{i}@proveedor.com",
                    "descripcion": "Proveedor generado automáticamente",
                },
            )
            proveedores.append(p)
        return proveedores

    def crear_materiales(self, catalogos, unidades):
        mapa_unidades = {u.codigo: u for u in unidades}
        data = [
            ("Cemento Gris 50kg", "BUL", "Cemento para construcción", "32000.00"),
            ("Arena de río", "M3", "Arena lavada", "95000.00"),
            ("Grava", "M3", "Grava triturada", "110000.00"),
            ("Ladrillo rojo", "UND", "Ladrillo estructural", "1200.00"),
            ("Varilla 3/8", "UND", "Varilla corrugada", "28000.00"),
            ("Pintura blanca 1 galón", "UND", "Pintura interior", "45000.00"),
            ("Cerámica piso", "M2", "Piso cerámico", "38000.00"),
            ("Yeso", "KG", "Yeso fino", "2500.00"),
            ("Bloque #5", "UND", "Bloque de concreto", "2800.00"),
            ("Pegante cerámico", "BUL", "Pegante en polvo", "29000.00"),
        ]
        materiales = []
        for i, (nombre, codigo_unidad, desc, precio) in enumerate(data, start=1):
            material, _ = MaterialConstruccion.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "catalogo": random.choice(catalogos),
                    "unidad_medida": mapa_unidades[codigo_unidad],
                    "descripcion": desc,
                    "precio_referencia": Decimal(precio),
                    "activo": True,
                },
            )
            materiales.append(material)
        return materiales

    def crear_stock(self, materiales):
        for material in materiales:
            Stock.objects.get_or_create(
                material=material,
                defaults={
                    "cantidad_actual": random.randint(20, 300),
                    "stock_minimo": random.randint(5, 20),
                    "ubicacion": f"Bodega-{random.randint(1, 5)}",
                },
            )

    def crear_metodos_pago(self):
        data = [
            ("EFECTIVO", "Efectivo"),
            ("TRANSFERENCIA", "Transferencia"),
            ("TARJETA", "Tarjeta"),
            ("NEQUI", "Nequi"),
        ]
        metodos = []
        for codigo, metodo in data:
            m, _ = MetodoPago.objects.get_or_create(
                codigo_metodo_pago=codigo,
                defaults={"metodo": metodo},
            )
            metodos.append(m)
        return metodos

    # -----------------------------
    # Compras
    # -----------------------------
    def crear_compras(self, cantidad, proveedores, materiales, usuarios_operativos):
        for i in range(1, cantidad + 1):
            compra = Compra.objects.create(
                proveedor=random.choice(proveedores),
                estado=random.choice(["pendiente", "recibida"]),
                usuario=random.choice(usuarios_operativos) if usuarios_operativos else None,
                observaciones=f"Compra demo #{i}",
            )

            seleccionados = random.sample(materiales, k=random.randint(2, min(4, len(materiales))))
            for material in seleccionados:
                precio = material.precio_referencia
                DetalleCompra.objects.create(
                    compra=compra,
                    material=material,
                    cantidad=random.randint(5, 40),
                    precio_unitario=precio,
                )

    # -----------------------------
    # Solicitudes de gestión
    # -----------------------------
    def crear_solicitudes(self, cantidad, clientes, materiales):
        for i in range(1, cantidad + 1):
            cliente = random.choice(clientes).usuario
            solicitud = SolicitudPedido.objects.create(
                cliente=cliente,
                estado=random.choice(["pendiente", "aprobado", "cancelado"]),
                descuento=Decimal(random.choice(["0.00", "5000.00", "10000.00"])),
            )

            seleccionados = random.sample(materiales, k=random.randint(1, min(4, len(materiales))))
            for material in seleccionados:
                DetalleSolicitudPedido.objects.create(
                    pedido=solicitud,
                    material=material,
                    cantidad=random.randint(1, 10),
                    precio_unitario=material.precio_referencia,
                )

    # -----------------------------
    # Pedidos / entregas
    # -----------------------------
    def crear_pedidos(self, cantidad, clientes, conductores, materiales):
        pedidos = []
        direcciones = [
            "Calle 10 # 20-30",
            "Carrera 50 # 12-14",
            "Avenida Principal # 99-10",
            "Transversal 23 # 45-67",
            "Bodega Industrial Zona Norte",
        ]

        for i in range(1, cantidad + 1):
            cliente = random.choice(clientes)
            conductor = random.choice(conductores).usuario if conductores and i % 2 == 0 else None

            pedido = Pedido.objects.create(
                usuario=cliente.usuario,
                cliente=cliente,
                estado=random.choice(["pendiente", "en_ruta", "entregado"]),
                direccion_origen="Bodega Central",
                direccion_destino=random.choice(direcciones),
                fecha_entrega_programada=timezone.now() + timedelta(days=random.randint(1, 7)),
                conductor=conductor,
            )

            seleccionados = random.sample(materiales, k=random.randint(1, min(4, len(materiales))))
            for material in seleccionados:
                DetallePedido.objects.create(
                    pedido=pedido,
                    material=material,
                    cantidad=random.randint(1, 12),
                    precio_unitario=material.precio_referencia,
                )

            if conductor:
                perfil_conductor = getattr(conductor, "perfil_conductor", None)
                vehiculo = perfil_conductor.vehiculo_actual if perfil_conductor else None
                Entrega.objects.create(
                    pedido=pedido,
                    conductor=conductor,
                    vehiculo=vehiculo,
                    fecha_salida=timezone.now(),
                    fecha_entrega=timezone.now() + timedelta(days=random.randint(1, 4)),
                    estado=random.choice(["pendiente", "en_ruta", "entregado"]),
                    direccion_entrega=pedido.direccion_destino,
                )

            pedidos.append(pedido)
        return pedidos

    # -----------------------------
    # Facturación / pagos
    # -----------------------------
    def crear_facturas_y_pagos(self, pedidos, metodos_pago, usuarios_operativos):
        for i, pedido in enumerate(pedidos, start=1):
            subtotal = pedido.total
            iva = (subtotal * Decimal("0.19")).quantize(Decimal("0.01"))
            total = (subtotal + iva).quantize(Decimal("0.01"))

            factura, creada = Factura.objects.get_or_create(
                pedido=pedido,
                defaults={
                    "cliente": pedido.cliente_usuario,
                    "numero": f"FAC-{timezone.now().year}-{i:05d}",
                    "subtotal": subtotal,
                    "iva": iva,
                    "total": total,
                    "estado": "pendiente",
                },
            )

            # En ~70% de las facturas genera pago
            if random.choice([True, True, True, False]):
                pago_total = random.choice([True, False])

                monto = total if pago_total else (total / Decimal("2")).quantize(Decimal("0.01"))
                Pago.objects.create(
                    factura=factura,
                    monto=monto,
                    codigo_metodo_pago=random.choice(metodos_pago),
                    referencia=f"REF-{factura.numero}",
                    registrado_por=random.choice(usuarios_operativos) if usuarios_operativos else None,
                )

                # Si quedó pendiente, a veces se completa
                if not pago_total and random.choice([True, False]):
                    restante = factura.total - factura.total_pagado
                    if restante > 0:
                        Pago.objects.create(
                            factura=factura,
                            monto=restante,
                            codigo_metodo_pago=random.choice(metodos_pago),
                            referencia=f"REF2-{factura.numero}",
                            registrado_por=random.choice(usuarios_operativos) if usuarios_operativos else None,
                        )

    # -----------------------------
    # Reportes / notificaciones
    # -----------------------------
    def crear_reportes(self, usuarios_operativos):
        tipos = ["inventario", "ventas", "compras", "entregas", "financiero"]

        for i, tipo in enumerate(tipos, start=1):
            reporte, _ = Reporte.objects.get_or_create(
                numero_reporte=f"REP-{timezone.now().year}-{i:04d}",
                defaults={
                    "tipo": tipo,
                    "estado": "generado",
                    "descripcion": f"Reporte automático de {tipo}",
                    "usuario": random.choice(usuarios_operativos) if usuarios_operativos else None,
                },
            )

            HistorialReporte.objects.get_or_create(
                codigo_historia=f"HIS-{timezone.now().year}-{i:04d}",
                defaults={
                    "reporte": reporte,
                    "descripcion": f"Creación inicial del reporte {reporte.numero_reporte}",
                },
            )

    def crear_notificaciones(self, clientes, conductores, usuarios_operativos):
        usuarios = [c.usuario for c in clientes] + [c.usuario for c in conductores] + usuarios_operativos
        for i, usuario in enumerate(usuarios[:15], start=1):
            Notificacion.objects.get_or_create(
                usuario=usuario,
                titulo=f"Notificación {i}",
                mensaje=f"Mensaje automático para {usuario.username}",
                defaults={
                    "tipo": random.choice(["info", "success", "warning"]),
                    "leida": False,
                    "link": "/usuarios/panel/",
                },
            )
