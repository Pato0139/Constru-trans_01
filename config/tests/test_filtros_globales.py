"""
Pruebas de integración de todos los filtros de tablas del sistema.

Verifica que cada vista con filtros:
  1. Responda HTTP 200 sin errores de ORM (FieldError, etc.)
  2. Devuelva únicamente los registros que coinciden con el criterio buscado
     y excluya los que no coinciden.
"""

from decimal import Decimal

from django.test import TestCase

from apps.catalogo.models import Catalogo, Marca, MaterialConstruccion, UnidadMedida
from apps.catalogo.models.movimientos import MovimientoInventario
from apps.clientes.models import Cliente
from apps.compras.models import Compra, Proveedor
from apps.logistica.models import Vehiculo
from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.usuarios.models import Usuario
from config.models import Historial


class FiltrosGlobalesIntegrationTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="Edward_Fonseca",
            email="edwardf5432@gmail.com",
            password="PasswordSeguro123!",
            nombres="Edward",
            apellidos="Fonseca",
            documento="10101010",
            rol="admin",
            estado="activo",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.admin)

        # Clientes de prueba
        self.u_andres = Usuario.objects.create_user(
            username="andres_cli",
            email="andres@test.com",
            password="PasswordSeguro123!",
            nombres="Andres",
            apellidos="Gomez",
            documento="20202020",
            rol="cliente",
            estado="activo",
        )
        self.cli_andres, _ = Cliente.objects.get_or_create(usuario=self.u_andres)

        self.u_camila = Usuario.objects.create_user(
            username="camila_cli",
            email="camila@test.com",
            password="PasswordSeguro123!",
            nombres="Camila",
            apellidos="Rojas",
            documento="30303030",
            rol="cliente",
            estado="inactivo",
        )
        self.cli_camila, _ = Cliente.objects.get_or_create(usuario=self.u_camila)

        # Pedidos
        self.pedido_andres = Pedido.objects.create(
            usuario=self.u_andres,
            cliente=self.cli_andres,
            direccion_destino="Calle 100 Norte Bogota",
            estado=Pedido.PENDIENTE,
            subtotal=Decimal("50000"),
            total=Decimal("50000"),
        )
        self.pedido_camila = Pedido.objects.create(
            usuario=self.u_camila,
            cliente=self.cli_camila,
            direccion_destino="Avenida Sur Medellin",
            estado=Pedido.ENTREGADO,
            subtotal=Decimal("80000"),
            total=Decimal("80000"),
        )

        # Pagos
        self.pago_andres = Pago.objects.create(
            pedido=self.pedido_andres,
            metodo="nequi",
            monto=Decimal("50000"),
            estado=Pago.PENDIENTE,
            comprobante="pagos/comprobante_andres.jpg",
        )
        self.pago_camila = Pago.objects.create(
            pedido=self.pedido_camila,
            metodo="transferencia",
            monto=Decimal("80000"),
            estado=Pago.APROBADO,
            comprobante="pagos/comprobante_camila.jpg",
        )

        # Vehículos
        self.veh_disp = Vehiculo.objects.create(
            placa="AAA111",
            tipo_vehiculo="Volqueta",
            capacidad_carga=Decimal("10.00"),
            estado="disponible",
        )
        self.veh_ruta = Vehiculo.objects.create(
            placa="BBB222",
            tipo_vehiculo="Camioneta",
            capacidad_carga=Decimal("3.00"),
            estado="en_ruta",
        )

        # Catálogo
        self.cat_cemento = Catalogo.objects.create(
            codigo_catalogo="CAT-CEM",
            nombre_empresa="Cementos",
            activo=True,
            estado="activo",
        )
        self.cat_acero = Catalogo.objects.create(
            codigo_catalogo="CAT-ACE",
            nombre_empresa="Aceros",
            activo=True,
            estado="activo",
        )
        self.marca_argos = Marca.objects.create(nombre="Argos", activo=True, estado="activo")
        self.marca_diaco = Marca.objects.create(nombre="Diaco", activo=True, estado="activo")
        self.unidad_bulto = UnidadMedida.objects.create(
            codigo="BTO", nombre="Bulto", abreviatura="Bto", activa=True
        )
        self.mat_cemento = MaterialConstruccion.objects.create(
            nombre="Cemento Gris 50kg",
            catalogo=self.cat_cemento,
            marca=self.marca_argos,
            unidad_medida=self.unidad_bulto,
            precio=Decimal("32000"),
            estado="activo",
            activo=True,
        )
        self.mat_varilla = MaterialConstruccion.objects.create(
            nombre="Varilla Corrugada 12mm",
            catalogo=self.cat_acero,
            marca=self.marca_diaco,
            unidad_medida=self.unidad_bulto,
            precio=Decimal("25000"),
            estado="activo",
            activo=True,
        )

        # Movimientos
        MovimientoInventario.objects.create(
            material=self.mat_cemento,
            tipo_movimiento="entrada",
            cantidad=20,
            usuario=self.admin,
            observacion="Ingreso inicial cemento",
        )
        MovimientoInventario.objects.create(
            material=self.mat_varilla,
            tipo_movimiento="salida",
            cantidad=5,
            usuario=self.u_andres,
            observacion="Despacho varilla",
        )

        # Proveedores y Compras
        self.prov_alfa = Proveedor.objects.create(
            nombre_empresa="Ferreteria Alfa",
            nit="900111222-1",
            contacto_nombre="Carlos Perez",
            telefono="3001112233",
            correo="alfa@test.com",
            ciudad="Bogota",
        )
        self.prov_beta = Proveedor.objects.create(
            nombre_empresa="Materiales Beta",
            nit="900333444-2",
            contacto_nombre="Laura Diaz",
            telefono="3004445566",
            correo="beta@test.com",
            ciudad="Cali",
        )
        Compra.objects.create(proveedor=self.prov_alfa, usuario=self.admin)
        Compra.objects.create(proveedor=self.prov_beta, usuario=self.admin)

        # Auditoría
        Historial.objects.create(
            usuario=self.admin,
            accion="crear",
            modulo="pedidos",
            descripcion="Creacion de pedido prueba",
        )
        Historial.objects.create(
            usuario=self.u_andres,
            accion="editar",
            modulo="catalogo",
            descripcion="Edicion de catalogo prueba",
        )

    def test_filtros_pedidos_lista_y_historial(self):
        # Filtro por q (código de pedido)
        r_q = self.client.get(
            "/pedidos/lista/",
            {"q": str(self.pedido_andres.codigo_pedido)},
        )
        self.assertEqual(r_q.status_code, 200)
        self.assertContains(r_q, "Calle 100 Norte Bogota")
        self.assertNotContains(r_q, "Avenida Sur Medellin")

        # Filtro por cliente (antes lanzaba FieldError: cliente__nombres)
        r_cli = self.client.get("/pedidos/lista/", {"cliente": "Andres"})
        self.assertEqual(r_cli.status_code, 200)
        self.assertContains(r_cli, "Calle 100 Norte Bogota")
        self.assertNotContains(r_cli, "Avenida Sur Medellin")

        # Filtro por destino
        r_dest = self.client.get("/pedidos/lista/", {"destino": "Norte Bogota"})
        self.assertEqual(r_dest.status_code, 200)
        self.assertContains(r_dest, "Calle 100 Norte Bogota")

        # Filtro por estado en historial
        r_hist = self.client.get("/pedidos/historial/", {"estado": Pedido.ENTREGADO})
        self.assertEqual(r_hist.status_code, 200)
        self.assertContains(r_hist, "Avenida Sur Medellin")
        self.assertNotContains(r_hist, "Calle 100 Norte Bogota")

        # Filtro AJAX
        r_ajax = self.client.get(
            "/pedidos/lista/",
            {"cliente": "Andres"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(r_ajax.status_code, 200)
        self.assertContains(r_ajax, "Calle 100 Norte Bogota")

    def test_filtros_pagos(self):
        # Antes lanzaba FieldError: pedido__cliente__nombres
        r_q = self.client.get("/pagos/", {"q": "Andres"})
        self.assertEqual(r_q.status_code, 200)
        self.assertContains(r_q, "Andres")
        self.assertNotContains(r_q, "Camila")

        r_est = self.client.get("/pagos/", {"estado": Pago.APROBADO})
        self.assertEqual(r_est.status_code, 200)
        self.assertContains(r_est, "Camila")
        self.assertNotContains(r_est, "Andres")

        r_met = self.client.get("/pagos/", {"metodo": "nequi"})
        self.assertEqual(r_met.status_code, 200)
        self.assertContains(r_met, "Andres")
        self.assertNotContains(r_met, "Camila")

    def test_filtros_vehiculos(self):
        r_placa = self.client.get("/logistica/vehiculos/", {"placa": "AAA111"})
        self.assertEqual(r_placa.status_code, 200)
        self.assertContains(r_placa, "AAA111")
        self.assertNotContains(r_placa, "BBB222")

        r_est = self.client.get("/logistica/vehiculos/", {"estado": "en_ruta"})
        self.assertEqual(r_est.status_code, 200)
        self.assertContains(r_est, "BBB222")
        self.assertNotContains(r_est, "AAA111")

    def test_filtros_clientes(self):
        r_q = self.client.get("/clientes/admin/lista/", {"q": "Andres"})
        self.assertEqual(r_q.status_code, 200)
        self.assertContains(r_q, "Andres")
        self.assertNotContains(r_q, "Camila")

        r_est = self.client.get("/clientes/admin/lista/", {"estado": "inactivo"})
        self.assertEqual(r_est.status_code, 200)
        self.assertContains(r_est, "Camila")
        self.assertNotContains(r_est, "Andres")

    def test_filtros_catalogo_materiales_tipos_marcas_unidades_movimientos(self):
        r_mat = self.client.get(
            "/catalogo/api/materiales/listado/",
            {"draw": "1", "start": "0", "length": "10", "material": "Cemento"},
        )
        self.assertEqual(r_mat.status_code, 200)
        payload = r_mat.json()
        self.assertEqual(payload["recordsFiltered"], 1)
        self.assertIn("Cemento Gris", payload["data"][0]["material"])

        r_tipo = self.client.get("/catalogo/tipos/", {"q": "Cementos"})
        self.assertEqual(r_tipo.status_code, 200)
        self.assertContains(r_tipo, "Cementos")
        self.assertNotContains(r_tipo, "Aceros")

        r_marca = self.client.get("/catalogo/marcas/", {"q": "Argos"})
        self.assertEqual(r_marca.status_code, 200)
        self.assertContains(r_marca, "Argos")
        self.assertNotContains(r_marca, "Diaco")

        r_mov_user = self.client.get("/catalogo/movimientos/", {"usuario": "Andres"})
        self.assertEqual(r_mov_user.status_code, 200)
        self.assertContains(r_mov_user, "Despacho varilla")
        self.assertNotContains(r_mov_user, "Ingreso inicial cemento")

        r_mov_tipo = self.client.get("/catalogo/movimientos/", {"tipo": "entrada"})
        self.assertEqual(r_mov_tipo.status_code, 200)
        self.assertContains(r_mov_tipo, "Ingreso inicial cemento")
        self.assertNotContains(r_mov_tipo, "Despacho varilla")

    def test_filtros_compras_y_proveedores(self):
        r_prov = self.client.get("/compras/proveedores/", {"q": "Alfa"})
        self.assertEqual(r_prov.status_code, 200)
        self.assertContains(r_prov, "Ferreteria Alfa")
        self.assertNotContains(r_prov, "Materiales Beta")

        r_comp = self.client.get("/compras/", {"proveedor": "Beta"})
        self.assertEqual(r_comp.status_code, 200)
        self.assertContains(r_comp, "Materiales Beta")
        self.assertNotContains(r_comp, "Ferreteria Alfa")

    def test_filtros_auditoria(self):
        r_aud = self.client.get("/auditoria/lista/", {"usuario": "Andres", "modulo": "catalogo"})
        self.assertEqual(r_aud.status_code, 200)
        self.assertContains(r_aud, "Edicion de catalogo prueba")
        self.assertNotContains(r_aud, "Creacion de pedido prueba")
