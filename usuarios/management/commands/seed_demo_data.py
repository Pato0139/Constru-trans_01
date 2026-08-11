from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from clientes.models import Cliente
from compras.models import Compra, DetalleCompra, ProveedorMaterial
from facturacion.models import Factura
from ordenes.models import Pedido, DetallePedido
from pagos.models import Pago, PagoPedido
from usuarios.models import (
    Catalogo,
    MaterialConstruccion,
    MetodoPago,
    Proveedor,
    Stock,
    UnidadMedida,
    Usuario,
    Vehiculo,
)


class Command(BaseCommand):
    help = "Crea un lote demo coherente para que las pantallas principales no queden vacías."

    def _reset_sequence(self, table_name, column_name):
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table_name}', '{column_name}'),
                    COALESCE((SELECT MAX({column_name}) FROM {table_name}), 0) + 1,
                    false
                )
                """
            )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Creando lote demo coherente...")
        for table_name, column_name in [
            ("material_construccion", "cod_material"),
            ("proveedor", "codigo_proveedor"),
            ("vehiculo", "id_vehiculo"),
            ("pedido", "codigo_pedido"),
            ("factura", "id_factura"),
            ("pago", "id_pago"),
            ("compra", "id_compra"),
        ]:
            self._reset_sequence(table_name, column_name)

        unidades = [
            {"codigo": "KG", "nombre": "Kilogramo", "abreviatura": "kg"},
            {"codigo": "M3", "nombre": "Metro cúbico", "abreviatura": "m³"},
            {"codigo": "UND", "nombre": "Unidad", "abreviatura": "Und"},
            {"codigo": "T", "nombre": "Tonelada", "abreviatura": "t"},
        ]
        for data in unidades:
            UnidadMedida.objects.update_or_create(
                codigo=data["codigo"],
                defaults={
                    "nombre": data["nombre"],
                    "abreviatura": data["abreviatura"],
                    "descripcion": f"Unidad estándar para {data['nombre']}",
                    "activa": True,
                    "orden": 0,
                },
            )

        catalogos = [
            ("METALES", "Metales y Acero"),
            ("AGREGADOS", "Arenas y Gravas"),
            ("CEMENTOS", "Cementos"),
            ("CERAMICOS", "Cerámicos"),
            ("TUBERIAS", "Tuberías y PVC"),
        ]
        for codigo, nombre in catalogos:
            Catalogo.objects.update_or_create(
                codigo_catalogo=codigo,
                defaults={"nombre_empresa": nombre},
            )

        materiales_seed = [
            {
                "nombre": "Alambre Negro Calibre 18 Kg",
                "catalogo": "METALES",
                "unidad": "KG",
                "precio": Decimal("8500"),
                "descripcion": "Alambre para amarre de obra",
                "stock": {"cantidad_actual": 1900, "stock_minimo": 200, "ubicacion": "Pasillo 10 - Bodega Principal"},
            },
            {
                "nombre": "Arena de Río",
                "catalogo": "AGREGADOS",
                "unidad": "M3",
                "precio": Decimal("78000"),
                "descripcion": "Arena lavada para mezcla",
                "stock": {"cantidad_actual": 1000, "stock_minimo": 150, "ubicacion": "Bodega Principal"},
            },
            {
                "nombre": "Grava Triturada 3/4",
                "catalogo": "AGREGADOS",
                "unidad": "M3",
                "precio": Decimal("92000"),
                "descripcion": "Grava para concreto",
                "stock": {"cantidad_actual": 850, "stock_minimo": 120, "ubicacion": "Patio Norte"},
            },
            {
                "nombre": "Cemento Gris 50 Kg",
                "catalogo": "CEMENTOS",
                "unidad": "UND",
                "precio": Decimal("36500"),
                "descripcion": "Saco de cemento gris",
                "stock": {"cantidad_actual": 420, "stock_minimo": 80, "ubicacion": "Bodega Cubierta A"},
            },
            {
                "nombre": "Varilla Corrugada 3/8",
                "catalogo": "METALES",
                "unidad": "UND",
                "precio": Decimal("28900"),
                "descripcion": "Varilla estructural",
                "stock": {"cantidad_actual": 300, "stock_minimo": 40, "ubicacion": "Zona Metales"},
            },
            {
                "nombre": "Ladrillo H10",
                "catalogo": "CERAMICOS",
                "unidad": "UND",
                "precio": Decimal("950"),
                "descripcion": "Ladrillo hueco",
                "stock": {"cantidad_actual": 15000, "stock_minimo": 2000, "ubicacion": "Patio Sur"},
            },
            {
                "nombre": "Tubo PVC 2 pulgadas",
                "catalogo": "TUBERIAS",
                "unidad": "UND",
                "precio": Decimal("21500"),
                "descripcion": "Tubo PVC sanitario",
                "stock": {"cantidad_actual": 180, "stock_minimo": 25, "ubicacion": "Pasillo 4"},
            },
            {
                "nombre": "Malla Electrosoldada 6 mm",
                "catalogo": "METALES",
                "unidad": "UND",
                "precio": Decimal("168000"),
                "descripcion": "Malla para refuerzo",
                "stock": {"cantidad_actual": 75, "stock_minimo": 10, "ubicacion": "Zona Metales"},
            },
        ]

        for material_data in materiales_seed:
            material = MaterialConstruccion.objects.update_or_create(
                nombre=material_data["nombre"],
                defaults={
                    "catalogo": Catalogo.objects.get(codigo_catalogo=material_data["catalogo"]),
                    "unidad_medida": UnidadMedida.objects.get(codigo=material_data["unidad"]),
                    "descripcion": material_data["descripcion"],
                    "precio_referencia": material_data["precio"],
                    "activo": True,
                },
            )[0]
            Stock.objects.update_or_create(
                material=material,
                defaults=material_data["stock"],
            )

        for codigo, metodo in [
            ("TRANSFER", "Transferencia"),
            ("EFECTIVO", "Efectivo"),
            ("TARJETA", "Tarjeta"),
            ("PSE", "PSE"),
            ("CREDITO", "Crédito a 30 días"),
        ]:
            obj, created = MetodoPago.objects.get_or_create(
                codigo_metodo_pago=codigo,
                defaults={"metodo": metodo},
            )
            if not created:
                existing_with_name = MetodoPago.objects.filter(metodo=metodo).exclude(pk=codigo).first()
                if existing_with_name is None and obj.metodo != metodo:
                    obj.metodo = metodo
                    obj.save(update_fields=["metodo"])

        proveedores_seed = [
            {
                "nombre_empresa": "Aceros Bogotá SAS",
                "nit": "900123456",
                "contacto_nombre": "Laura Méndez",
                "telefono": "3001234567",
                "correo": "compras@acerosbogota.com",
                "ciudad": "Bogotá",
                "categoria": "Metales",
            },
            {
                "nombre_empresa": "Cales y Arenas SAS",
                "nit": "901456789",
                "contacto_nombre": "Felipe Rojas",
                "telefono": "3015557788",
                "correo": "ventas@calesyarenas.com",
                "ciudad": "Soacha",
                "categoria": "Agregados",
            },
            {
                "nombre_empresa": "Ladrillera Central",
                "nit": "800987123",
                "contacto_nombre": "Sonia Parra",
                "telefono": "3204448899",
                "correo": "pedidos@ladrilleracentral.com",
                "ciudad": "Bogotá",
                "categoria": "Cerámicos",
            },
            {
                "nombre_empresa": "PVC Industrial Colombia",
                "nit": "901222333",
                "contacto_nombre": "Andrés Pineda",
                "telefono": "3108887766",
                "correo": "comercial@pvcindustrial.co",
                "ciudad": "Funza",
                "categoria": "Tuberías",
            },
        ]
        proveedores = {}
        for data in proveedores_seed:
            proveedor, _ = Proveedor.objects.update_or_create(
                nit=data["nit"],
                defaults={
                    "nombre_empresa": data["nombre_empresa"],
                    "contacto_nombre": data["contacto_nombre"],
                    "telefono": data["telefono"],
                    "correo": data["correo"],
                    "ciudad": data["ciudad"],
                    "categoria": data["categoria"],
                    "direccion": data.get("ciudad", ""),
                    "activo": True,
                },
            )
            proveedores[data["nombre_empresa"]] = proveedor

        vehiculos_seed = [
            ("FTX291", "Chevrolet", "NHR 2021", "Camión Estacas", Decimal("7.00"), "disponible"),
            ("KLM482", "International", "DuraStar 2020", "Tractomula", Decimal("18.00"), "disponible"),
            ("JQR155", "Hino", "300 2022", "Volqueta", Decimal("9.00"), "en_ruta"),
            ("TPA908", "JAC", "JHR 2023", "Camión Liviano", Decimal("4.50"), "mantenimiento"),
            ("MNS774", "Kenworth", "T800 2019", "Tractocamión", Decimal("20.00"), "disponible"),
            ("BQE640", "Ford", "Cargo 2021", "Camión Estacas", Decimal("8.50"), "disponible"),
        ]
        for placa, marca, modelo, tipo, capacidad, estado in vehiculos_seed:
            Vehiculo.objects.update_or_create(
                placa=placa,
                defaults={
                    "marca": marca,
                    "modelo": modelo,
                    "tipo_vehiculo": tipo,
                    "capacidad_carga": capacidad,
                    "estado": estado,
                },
            )

        users = []
        for username, nombres, apellidos, rol, documento in [
            ("cliente1", "Carlos", "Ramírez", "cliente", "1022334455"),
            ("cliente2", "Mariana", "López", "cliente", "1033445566"),
            ("cliente3", "Constructora Andina", "SAS", "cliente", "900778899"),
            ("conductor1", "Diego", "Torres", "conductor", "79887766"),
            ("admin1", "Edward", "Admin", "admin", "100000001"),
        ]:
            user, created = Usuario.objects.update_or_create(
                username=username,
                defaults={
                    "nombres": nombres,
                    "apellidos": apellidos,
                    "rol": rol,
                    "documento": documento,
                    "tipo_documento": "CC",
                    "email": f"{username}@demo.local",
                    "estado": "activo",
                    "is_active": True,
                },
            )
            user.set_password("demo1234")
            user.save()
            users.append(user)

        clientes_por_user = {
            "cliente1": Cliente.objects.get(usuario__username="cliente1"),
            "cliente2": Cliente.objects.get(usuario__username="cliente2"),
            "cliente3": Cliente.objects.get(usuario__username="cliente3"),
        }

        materiales = {m.nombre: m for m in MaterialConstruccion.objects.all()}
        pedidos_seed = [
            {
                "codigo": 101,
                "usuario": "cliente1",
                "cliente": "cliente1",
                "destino": "Calle 80 # 72-15, Bogotá",
                "estado": "pendiente",
                "detalles": [
                    ("Cemento Gris 50 Kg", 20, Decimal("36500")),
                    ("Arena de Río", 8, Decimal("78000")),
                ],
            },
            {
                "codigo": 102,
                "usuario": "cliente2",
                "cliente": "cliente2",
                "destino": "Cra 15 # 134-22, Bogotá",
                "estado": "autorizado_despacho",
                "detalles": [
                    ("Grava Triturada 3/4", 12, Decimal("92000")),
                    ("Varilla Corrugada 3/8", 60, Decimal("28900")),
                ],
            },
            {
                "codigo": 103,
                "usuario": "cliente3",
                "cliente": "cliente3",
                "destino": "Vía Siberia Km 3, Cota",
                "estado": "entregado",
                "detalles": [
                    ("Ladrillo H10", 3000, Decimal("950")),
                    ("Malla Electrosoldada 6 mm", 40, Decimal("168000")),
                ],
            },
            {
                "codigo": 104,
                "usuario": "cliente1",
                "cliente": "cliente1",
                "destino": "Soacha Compartir, Bodega 4",
                "estado": "en_ruta",
                "detalles": [
                    ("Tubo PVC 2 pulgadas", 10, Decimal("21500")),
                    ("Cemento Gris 50 Kg", 10, Decimal("36500")),
                ],
            },
            {
                "codigo": 105,
                "usuario": "cliente2",
                "cliente": "cliente2",
                "destino": "Chía, Vereda La Balsa",
                "estado": "vehiculo_asignado",
                "detalles": [
                    ("Arena de Río", 5, Decimal("78000")),
                    ("Grava Triturada 3/4", 5, Decimal("92000")),
                    ("Varilla Corrugada 3/8", 25, Decimal("28900")),
                ],
            },
        ]

        for data in pedidos_seed:
            pedido, _ = Pedido.objects.update_or_create(
                codigo_pedido=data["codigo"],
                defaults={
                    "usuario": Usuario.objects.get(username=data["usuario"]),
                    "cliente": clientes_por_user[data["cliente"]],
                    "direccion_destino": data["destino"],
                    "estado": data["estado"],
                },
            )
            for nombre, cantidad, precio_unitario in data["detalles"]:
                DetallePedido.objects.update_or_create(
                    pedido=pedido,
                    material=materiales[nombre],
                    defaults={
                        "cantidad": cantidad,
                        "precio_unitario": precio_unitario,
                    },
                )
            pedido.calcular_total()

        facturas_seed = [
            ("FAC-2026-001", 101, "cliente1", Decimal("1243697"), Decimal("236303"), Decimal("1480000"), "pendiente"),
            ("FAC-2026-002", 102, "cliente2", Decimal("2470588"), Decimal("469412"), Decimal("2940000"), "pendiente"),
            ("FAC-2026-003", 103, "cliente3", Decimal("6285714"), Decimal("1194286"), Decimal("7480000"), "pagada"),
            ("FAC-2026-004", 104, "cliente1", Decimal("823529"), Decimal("156471"), Decimal("980000"), "pendiente"),
            ("FAC-2026-005", 105, "cliente2", Decimal("1890756"), Decimal("359244"), Decimal("2250000"), "pendiente"),
        ]
        for numero, pedido_id, cliente_username, subtotal, iva, total, estado in facturas_seed:
            factura, _ = Factura.objects.update_or_create(
                numero=numero,
                defaults={
                    "pedido": Pedido.objects.get(codigo_pedido=pedido_id),
                    "cliente": Usuario.objects.get(username=cliente_username),
                    "subtotal": subtotal,
                    "iva": iva,
                    "total": total,
                    "estado": estado,
                },
            )

        pagados_seed = [
            ("FAC-2026-001", Decimal("500000"), "TRANSFER", "TRX-90001", "admin1"),
            ("FAC-2026-002", Decimal("1000000"), "PSE", "PSE-44021", "admin1"),
            ("FAC-2026-003", Decimal("7480000"), "TRANSFER", "TRX-90003", "admin1"),
            ("FAC-2026-004", Decimal("300000"), "EFECTIVO", "CAJA-1204", "admin1"),
        ]
        for numero, monto, codigo_pago, referencia, registrado_por in pagados_seed:
            factura = Factura.objects.get(numero=numero)
            Pago.objects.update_or_create(
                factura=factura,
                monto=monto,
                codigo_metodo_pago=MetodoPago.objects.get(codigo_metodo_pago=codigo_pago),
                defaults={
                    "referencia": referencia,
                    "registrado_por": Usuario.objects.get(username=registrado_por),
                },
            )

        for pedido_id, cliente_username, monto, metodo, estado, referencia in [
            (101, "cliente1", Decimal("500000"), "Transferencia", "en_revision", "COMP-101-A"),
            (102, "cliente2", Decimal("1000000"), "PSE", "pago aprobado", "COMP-102-A"),
            (103, "cliente3", Decimal("7480000"), "Transferencia", "pago aprobado", "COMP-103-A"),
            (104, "cliente1", Decimal("300000"), "Efectivo", "pendiente", "REC-104-A"),
            (105, "cliente2", Decimal("0"), "Contra entrega", "contra_entrega", "COD-105"),
        ]:
            PagoPedido.objects.update_or_create(
                pedido=Pedido.objects.get(codigo_pedido=pedido_id),
                defaults={
                    "cliente": clientes_por_user[cliente_username],
                    "metodo_pago": metodo,
                    "estado_pago": estado,
                    "monto": monto,
                    "referencia": referencia,
                },
            )

        compras_seed = [
            {
                "proveedor": "Aceros Bogotá SAS",
                "materiales": [
                    ("Varilla Corrugada 3/8", 40, Decimal("28900")),
                    ("Malla Electrosoldada 6 mm", 8, Decimal("168000")),
                ],
                "estado": "recibida",
                "usuario": "admin1",
            },
            {
                "proveedor": "Cales y Arenas SAS",
                "materiales": [
                    ("Arena de Río", 18, Decimal("78000")),
                    ("Grava Triturada 3/4", 12, Decimal("92000")),
                ],
                "estado": "pendiente",
                "usuario": "admin1",
            },
            {
                "proveedor": "Ladrillera Central",
                "materiales": [
                    ("Ladrillo H10", 7874, Decimal("950")),
                ],
                "estado": "recibida",
                "usuario": "admin1",
            },
            {
                "proveedor": "PVC Industrial Colombia",
                "materiales": [
                    ("Tubo PVC 2 pulgadas", 60, Decimal("21500")),
                ],
                "estado": "pendiente",
                "usuario": "admin1",
            },
        ]

        for idx, data in enumerate(compras_seed, start=1):
            compra, _ = Compra.objects.update_or_create(
                id_compra=idx,
                defaults={
                    "proveedor": proveedores[data["proveedor"]],
                    "estado": data["estado"],
                    "usuario": Usuario.objects.get(username=data["usuario"]),
                },
            )
            for nombre, cantidad, precio in data["materiales"]:
                DetalleCompra.objects.update_or_create(
                    compra=compra,
                    material=materiales[nombre],
                    defaults={
                        "cantidad": cantidad,
                        "precio_unitario": precio,
                    },
                )
            compra.calcular_total()

            ProveedorMaterial.objects.update_or_create(
                proveedor=proveedores[data["proveedor"]],
                material=materiales[data["materiales"][0][0]],
                defaults={"precio_actual": data["materiales"][0][2]},
            )

        self.stdout.write(self.style.SUCCESS("Lote demo cargado correctamente."))
