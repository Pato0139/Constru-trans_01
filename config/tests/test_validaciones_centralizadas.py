from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.compras.models import Compra, DetalleCompra, Proveedor
from apps.pagos.models import Factura, Pago, PagoFactura
from apps.pedidos.models import DetallePedido, Pedido
from apps.usuarios.models import Usuario
from config.sequences import numero_factura


class ValidacionesCentralizadasTests(TestCase):
    def setUp(self):
        self.usuario_cliente = Usuario.objects.create_user(
            username="cliente_test",
            email="cliente_test@constru.com",
            password="Password123!",
            nombres="Carlos",
            apellidos="Perez",
            documento="1020304050",
            tipo_documento="CC",
            rol="cliente",
        )
        self.cliente = Cliente.objects.get(usuario=self.usuario_cliente)

    # -------------------------------------------------------------------------
    # PEDIDOS
    # -------------------------------------------------------------------------
    def test_pedido_transicion_valida_y_bloqueo_reversa(self):
        """Verifica que el pedido siga su flujo y bloquee regresiones arbitrarias."""
        pedido = Pedido.objects.create(
            usuario=self.usuario_cliente,
            direccion_destino="Calle 10 # 20-30",
            subtotal=Decimal("100000.00"),
            impuesto=Decimal("19000.00"),
            descuento=Decimal("0.00"),
            total=Decimal("119000.00"),
            impuesto_porcentaje=Decimal("19.00"),
            estado=Pedido.PENDIENTE,
        )

        # Transición permitida
        pedido.transicionar(Pedido.AUTORIZADO_DESPACHO)
        pedido.save()
        self.assertEqual(pedido.estado, Pedido.AUTORIZADO_DESPACHO)

        pedido.transicionar(Pedido.EN_RUTA)
        pedido.save()
        self.assertEqual(pedido.estado, Pedido.EN_RUTA)

        pedido.transicionar(Pedido.ENTREGADO)
        pedido.save()
        self.assertEqual(pedido.estado, Pedido.ENTREGADO)

        # Transición prohibida desde entregado
        with self.assertRaises(ValidationError):
            pedido.transicionar(Pedido.PENDIENTE)

    def test_pedido_clean_montos_incoherentes(self):
        """clean() debe fallar si total != subtotal + impuesto - descuento."""
        pedido = Pedido(
            usuario=self.usuario_cliente,
            direccion_destino="Calle 10",
            subtotal=Decimal("100000.00"),
            impuesto=Decimal("19000.00"),
            descuento=Decimal("0.00"),
            total=Decimal("50000.00"),  # Incoherente
            impuesto_porcentaje=Decimal("19.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            pedido.clean()
        self.assertIn("total", ctx.exception.message_dict)

    def test_pedido_impuesto_porcentaje_fuera_de_rango(self):
        """El porcentaje de impuesto no puede superar 100."""
        pedido = Pedido(
            usuario=self.usuario_cliente,
            direccion_destino="Calle 10",
            subtotal=Decimal("100000.00"),
            impuesto=Decimal("0.00"),
            descuento=Decimal("0.00"),
            total=Decimal("100000.00"),
            impuesto_porcentaje=Decimal("150.00"),  # > 100
        )
        with self.assertRaises(ValidationError) as ctx:
            pedido.clean()
        self.assertIn("impuesto_porcentaje", ctx.exception.message_dict)

    # -------------------------------------------------------------------------
    # COMPRAS
    # -------------------------------------------------------------------------
    def test_compra_transiciones(self):
        """Verifica que una compra pendiente pueda recibirse o cancelarse, pero no revertirse."""
        proveedor = Proveedor.objects.create(
            nombre_empresa="Aceros de Colombia",
            nit="900123456-1",
            telefono="3101234567",
        )
        compra = Compra.objects.create(
            proveedor=proveedor,
            usuario=self.usuario_cliente,
            estado="pendiente",
        )

        compra.transicionar("recibida")
        compra.save()
        self.assertEqual(compra.estado, "recibida")

        # Desde recibida no se puede cancelar ni volver a pendiente
        with self.assertRaises(ValidationError):
            compra.transicionar("pendiente")

        with self.assertRaises(ValidationError):
            compra.transicionar("cancelada")

    # -------------------------------------------------------------------------
    # CLIENTES
    # -------------------------------------------------------------------------
    def test_cliente_empresa_exige_nit_y_nombre(self):
        """Cliente tipo empresa debe exigir NIT y razón social."""
        self.cliente.tipo_cliente = "empresa"
        self.cliente.nit = ""
        self.cliente.nombre_empresa = ""

        with self.assertRaises(ValidationError) as ctx:
            self.cliente.clean()
        self.assertIn("nit", ctx.exception.message_dict)
        self.assertIn("nombre_empresa", ctx.exception.message_dict)

    # -------------------------------------------------------------------------
    # CONSECUTIVOS DE FACTURACIÓN
    # -------------------------------------------------------------------------
    def test_generador_consecutivos_incrementa_ordenadamente(self):
        """numero_factura() debe generar F-AAAA-00001, F-AAAA-00002 de forma consecutiva."""
        anio = timezone.now().year
        num1 = numero_factura(anio)
        num2 = numero_factura(anio)

        self.assertTrue(num1.startswith(f"F-{anio}-"))
        self.assertTrue(num2.startswith(f"F-{anio}-"))

        sec1 = int(num1.split("-")[-1])
        sec2 = int(num2.split("-")[-1])
        self.assertEqual(sec2, sec1 + 1)

    # -------------------------------------------------------------------------
    # LOGÍSTICA
    # -------------------------------------------------------------------------
    def test_vehiculo_transiciones_y_placa_invalida(self):
        """Vehiculo debe validar el formato de placa y transiciones de estado."""
        from apps.logistica.models import Vehiculo

        # Placa inválida (con caracteres extraños o minúsculas)
        vehiculo = Vehiculo(
            placa="123",  # Demasiado corta
            marca="Chevrolet",
            modelo="NPR",
            tipo_vehiculo="Camión",
            capacidad_carga=Decimal("5.0"),
            estado="disponible",
        )
        with self.assertRaises(ValidationError):
            vehiculo.full_clean()

        # Placa válida
        vehiculo.placa = "CTV0336"
        vehiculo.full_clean()
        vehiculo.save()

        # Transición de estado permitida
        vehiculo.transicionar("en_ruta")
        vehiculo.save()
        self.assertEqual(vehiculo.estado, "en_ruta")

        # Transición válida de vuelta a disponible
        vehiculo.transicionar("disponible")
        vehiculo.save()
        self.assertEqual(vehiculo.estado, "disponible")

    def test_entrega_transiciones(self):
        """Entrega debe bloquear transiciones ilegales."""
        from apps.logistica.models import Entrega

        entrega = Entrega(
            estado="pendiente",
            direccion_entrega="Av Principal 123",
        )
        # Transición legal
        entrega.transicionar("en_ruta")
        self.assertEqual(entrega.estado, "en_ruta")

        entrega.transicionar("entregado")
        self.assertEqual(entrega.estado, "entregado")

        # Transición prohibida desde entregado (estado terminal)
        with self.assertRaises(ValidationError):
            entrega.transicionar("pendiente")

    # -------------------------------------------------------------------------
    # CATÁLOGO
    # -------------------------------------------------------------------------
    def test_material_form_rechaza_campos_extra_y_precios_negativos(self):
        """MaterialForm (StrictModelForm) debe rechazar inyección de parámetros y valores negativos."""
        from apps.catalogo.forms import MaterialForm
        from apps.catalogo.models import UnidadMedida

        unidad, _ = UnidadMedida.objects.get_or_create(
            codigo="UND", defaults={"nombre": "Unidad", "abreviatura": "und", "activa": True}
        )

        # 1. Parámetro no permitido (Mass Assignment)
        form_extra = MaterialForm(
            data={
                "nombre": "Cemento Gris",
                "unidad_medida": unidad.pk,
                "precio_referencia": "25000",
                "parametro_falso_hacker": "inyeccion",
            }
        )
        self.assertFalse(form_extra.is_valid())
        self.assertIn("parametro_falso_hacker", str(form_extra.errors))

        # 2. Precio negativo
        form_negativo = MaterialForm(
            data={
                "nombre": "Cemento Gris",
                "unidad_medida": unidad.pk,
                "precio_referencia": "-100",
            }
        )
        self.assertFalse(form_negativo.is_valid())
        self.assertIn("precio_referencia", form_negativo.errors)

