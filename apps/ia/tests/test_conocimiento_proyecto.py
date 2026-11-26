from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.auditoria.models import Historial
from apps.catalogo.models import Catalogo, Marca, MaterialConstruccion, Stock, UnidadMedida
from apps.clientes.models import Cliente
from apps.compras.models import Proveedor
from apps.ia.services import assistant_service, orm_query_service, project_knowledge_service
from apps.logistica.models import Vehiculo
from apps.pagos.models import Pago
from apps.pedidos.models import Pedido

User = get_user_model()


class ProjectKnowledgeTests(TestCase):
    def test_cubre_todos_los_modulos_funcionales(self):
        casos = [
            ("¿Cómo funciona el captcha en el login?", "CAPTCHA"),
            ("¿Cómo cambio mi contraseña?", "Cambiar Contraseña"),
            ("¿Cómo subo mi foto de perfil o avatar?", "Mi Perfil"),
            ("¿Cómo funciona el modo híbrido con Neon y SQLite?", "El Celador"),
            ("¿Qué métodos de pago aceptan?", "Nequi"),
            ("¿Cómo funciona la tarifa de envío y los estados de pedido?", "Autorizado para despacho"),
            ("¿Cómo reporto una novedad en logística?", "Novedades"),
            ("¿Cómo funcionan las entradas y salidas de inventario?", "Movimientos de Inventario"),
            ("¿Cómo registro proveedores y órdenes de compra?", "Proveedores"),
            ("¿Qué reportes puedo exportar en PDF y Excel?", "Reportes"),
            ("¿Qué guarda el módulo de auditoría?", "Auditoría"),
            ("¿Tienen modo oscuro y filtros de daltonismo?", "Accesibilidad"),
            ("¿Dónde descargo el manual del administrador?", "Centro de Ayuda"),
            ("¿Cómo instalar el proyecto con setup o Docker?", "setup_windows.ps1"),
            ("¿Qué roles existen y qué módulos tiene el proyecto?", "Roles y Módulos"),
        ]
        for pregunta, esperado in casos:
            resp = project_knowledge_service.responder_conocimiento_proyecto(pregunta)
            self.assertIsNotNone(resp, f"No respondió: {pregunta}")
            self.assertIn(esperado, resp, f"Faltó '{esperado}' para: {pregunta}")

    def test_no_secuestra_preguntas_generales(self):
        self.assertIsNone(
            project_knowledge_service.responder_conocimiento_proyecto("¿Quién fue Simón Bolívar?")
        )
        self.assertIsNone(
            project_knowledge_service.responder_conocimiento_proyecto("¿Qué es la fotosíntesis?")
        )


class ExtendedORMQueryTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_ia",
            email="admin_ia@test.com",
            password="TestPassword123!",
            nombres="Edward",
            apellidos="Admin",
            rol="admin",
            estado="activo",
        )
        self.cliente_u = User.objects.create_user(
            username="cliente_ia",
            email="cliente_ia@test.com",
            password="TestPassword123!",
            nombres="Maria",
            apellidos="Perez",
            rol="cliente",
            estado="activo",
        )
        self.cliente, _ = Cliente.objects.get_or_create(usuario=self.cliente_u)
        self.cat = Catalogo.objects.create(
            codigo_catalogo="CAT-IA", nombre_empresa="Cementos IA", activo=True
        )
        self.marca = Marca.objects.create(nombre="Argos IA", activo=True)
        self.unidad = UnidadMedida.objects.create(
            codigo="BTO", nombre="Bulto", abreviatura="Bto", activa=True
        )
        self.mat = MaterialConstruccion.objects.create(
            nombre="Cemento Blanco",
            catalogo=self.cat,
            marca=self.marca,
            unidad_medida=self.unidad,
            precio=Decimal("42000"),
            activo=True,
        )
        Stock.objects.update_or_create(
            material=self.mat, defaults={"cantidad_actual": 2, "stock_minimo": 10}
        )
        self.pedido = Pedido.objects.create(
            usuario=self.cliente_u,
            cliente=self.cliente,
            direccion_destino="Calle 50 #10-20",
            estado=Pedido.PENDIENTE,
            subtotal=Decimal("42000"),
            total=Decimal("42000"),
        )
        Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_NEQUI,
            monto=Decimal("42000"),
            estado=Pago.PENDIENTE,
        )
        Vehiculo.objects.create(
            placa="XYZ987",
            marca="Hino",
            modelo="2024",
            tipo_vehiculo="Volqueta",
            capacidad_carga=Decimal("12.00"),
            estado="disponible",
        )
        Proveedor.objects.create(
            nombre_empresa="Cementera Nacional",
            nit="900555666-1",
            contacto_nombre="Luis",
            telefono="3001234567",
            correo="luis@cementera.com",
            ciudad="Bogota",
        )
        Historial.objects.create(
            usuario=self.admin,
            accion="crear",
            modulo="pedidos",
            descripcion="Creación de prueba IA",
        )

    def test_consultas_orm_en_tiempo_real_admin(self):
        r_pagos = orm_query_service.consultar_datos("¿Qué pagos pendientes hay?", self.admin)
        self.assertIn("Nequi", r_pagos)

        r_veh = orm_query_service.consultar_datos("¿Qué vehículos disponibles hay?", self.admin)
        self.assertIn("XYZ987", r_veh)

        r_marcas = orm_query_service.consultar_datos("¿Cuáles marcas hay?", self.admin)
        self.assertIn("Argos IA", r_marcas)

        r_stock = orm_query_service.consultar_datos("¿Qué materiales tienen stock bajo?", self.admin)
        self.assertIn("Cemento Blanco", r_stock)

        r_prov = orm_query_service.consultar_datos("Lista de proveedores", self.admin)
        self.assertIn("Cementera Nacional", r_prov)

        r_aud = orm_query_service.consultar_datos("Ver últimas acciones de auditoría", self.admin)
        self.assertIn("Creación de prueba IA", r_aud)

        r_perf = orm_query_service.consultar_datos("¿Quién soy? ver mis datos", self.admin)
        self.assertIn("Edward Admin", r_perf)

        r_ped = orm_query_service.consultar_datos(
            f"Estado del pedido #{self.pedido.codigo_pedido}", self.admin
        )
        self.assertIn("Maria Perez", r_ped)
        self.assertIn("Nequi", r_ped)

    def test_seguridad_por_rol_cliente(self):
        r_aud = orm_query_service.consultar_datos("Ver últimas acciones de auditoría", self.cliente_u)
        self.assertIn("solo puede ser consultado por administradores", r_aud)

        r_prov = orm_query_service.consultar_datos("Lista de proveedores", self.cliente_u)
        self.assertIn("exclusivo para administradores", r_prov)

    def test_preguntar_ia_integrado_sin_llm(self):
        resp, msg_id = assistant_service.preguntar_ia(
            "¿Cómo funciona el modo híbrido con Neon y SQLite?",
            usuario=self.admin,
            session_id="test-proj-kb",
        )
        self.assertIsNotNone(msg_id)
        self.assertIn("El Celador", resp)
