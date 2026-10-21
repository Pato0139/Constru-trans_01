"""
Pruebas de seguridad y validaciones estrictas (Área 2)
Reproduce fallos de seguridad en formularios y vistas que no usaban
validaciones estrictas en backend como única fuente de verdad.
"""

from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.ayuda.forms import SugerenciaForm
from apps.catalogo.models import MaterialConstruccion, Stock, UnidadMedida
from apps.pedidos.forms_pagos import PagoRegistroForm
from apps.pedidos.models import Pedido
from apps.usuarios.forms import FotoPerfilForm, RegistroForm, UsuarioForm
from apps.usuarios.models import Usuario
from config.forms_base import StrictForm, StrictModelForm


class SeguridadArea2ValidacionesTests(TestCase):
    def setUp(self):
        self.unidad = UnidadMedida.objects.create(
            codigo="UND",
            nombre="Unidad",
            abreviatura="und",
        )
        self.material = MaterialConstruccion.objects.create(
            nombre="Arena Lavada",
            unidad_medida=self.unidad,
            precio_referencia=Decimal("50000.00"),
        )
        self.cliente = Usuario.objects.create_user(
            username="cliente_sec@test.com",
            email="cliente_sec@test.com",
            password="Password123*",
            nombres="Cliente",
            apellidos="Seguridad",
            documento="77112233",
            tipo_documento="CC",
            rol="cliente",
        )
        self.admin = Usuario.objects.create_user(
            username="admin_sec@test.com",
            email="admin_sec@test.com",
            password="Password123*",
            nombres="Admin",
            apellidos="Seguridad",
            documento="77112244",
            tipo_documento="CC",
            rol="admin",
        )
        self.pedido = Pedido.objects.create(
            usuario=self.cliente,
            direccion_destino="Calle 100 # 15-20, Bogotá",
            estado=Pedido.PENDIENTE,
            total=Decimal("150000.00"),
        )
        self.stock, _ = Stock.objects.get_or_create(
            material=self.material,
            defaults={"cantidad_actual": 100, "ubicacion": "Bodega 1"},
        )

    def test_registro_form_es_strict_y_rechaza_mass_assignment_rol_o_staff(self):
        """RegistroForm debe rechazar payloads que intenten inyectar rol o is_staff."""
        self.assertTrue(
            issubclass(RegistroForm, (StrictModelForm, StrictForm)),
            "RegistroForm debe heredar de StrictModelForm",
        )
        data = {
            "nombres": "Juan Carlos",
            "apellidos": "Pérez Gómez",
            "tipo_documento": "CC",
            "documento": "1098765432",
            "telefono": "3001234567",
            "correo": "atacante@test.com",
            "pais_codigo": "+57",
            "contrasena": "Password123*",
            "confirmar_contrasena": "Password123*",
            "aceptar_terminos": "yes",
            # Inyección maliciosa
            "rol": "admin",
            "is_staff": "True",
            "is_superuser": "True",
        }
        form = RegistroForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertTrue(
            any(
                code == "campos_desconocidos"
                for code_list in form.errors.as_data().values()
                for code in [item.code for item in code_list]
            ),
            "RegistroForm debe rechazar campos no declarados como rol/is_staff",
        )

    def test_pago_registro_form_es_strict_y_rechaza_campos_no_declarados(self):
        """PagoRegistroForm debe heredar de StrictModelForm y rechazar 'monto' o 'estado'."""
        self.assertTrue(
            issubclass(PagoRegistroForm, (StrictModelForm, StrictForm)),
            "PagoRegistroForm debe heredar de StrictModelForm",
        )
        data = {
            "metodo": "contraentrega",
            "monto": "1.00",  # El cliente intenta fijar un monto arbitrario
            "estado": "aprobado",  # El cliente intenta auto-aprobarse
        }
        form = PagoRegistroForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertTrue(
            any(
                "campos_desconocidos" in [item.code for item in code_list]
                for code_list in form.errors.as_data().values()
            ),
            "PagoRegistroForm debe marcar error por campos desconocidos en el payload",
        )

    def test_foto_perfil_rechaza_archivo_con_magic_bytes_falsos(self):
        """FotoPerfilForm debe validar la firma real de los bytes y rechazar scripts."""
        self.assertTrue(
            issubclass(FotoPerfilForm, (StrictModelForm, StrictForm)),
            "FotoPerfilForm debe heredar de StrictForm",
        )
        # Archivo que simula extensión .jpg pero su contenido es un script de texto
        falso_jpg = SimpleUploadedFile(
            "malicioso.jpg",
            b"<?php echo 'hacked'; ?>",
            content_type="image/jpeg",
        )
        form = FotoPerfilForm(files={"foto_perfil": falso_jpg})
        self.assertFalse(form.is_valid())
        self.assertIn("foto_perfil", form.errors)

    def test_sugerencia_form_es_strict_y_rechaza_estado_o_usuario(self):
        """SugerenciaForm debe rechazar inyección de estado o asignación de usuario."""
        self.assertTrue(
            issubclass(SugerenciaForm, (StrictModelForm, StrictForm)),
            "SugerenciaForm debe heredar de StrictModelForm",
        )
        data = {
            "tipo": "sugerencia",
            "titulo": "Mejora en la interfaz",
            "descripcion": "Sería conveniente agregar filtro por fechas",
            "estado": "implementado",
            "usuario_id": "1",
        }
        form = SugerenciaForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertTrue(
            any(
                "campos_desconocidos" in [item.code for item in code_list]
                for code_list in form.errors.as_data().values()
            )
        )

    def test_registro_rechaza_sin_aceptar_terminos(self):
        """El backend rechaza terminantemente el registro sin aceptación de términos."""
        data = {
            "nombres": "Pedro",
            "apellidos": "Navaja",
            "tipo_documento": "CC",
            "documento": "987654321",
            "telefono": "3109876543",
            "correo": "pedro@test.com",
            "pais_codigo": "+57",
            "contrasena": "Password123*",
            "confirmar_contrasena": "Password123*",
            # Omitiendo aceptar_terminos
        }
        form = RegistroForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("aceptar_terminos", form.errors)

    def test_editar_stock_rechaza_cantidad_negativa(self):
        """La vista de stock o su validador debe rechazar cantidades negativas en backend."""
        stock = Stock.objects.get(material=self.material)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("catalogo:editar_stock", args=[self.material.id]),
            {"cantidad": "-50", "ubicacion": "Bodega Principal"},
        )
        stock.refresh_from_db()
        self.assertNotEqual(stock.cantidad_actual, -50)
        self.assertGreaterEqual(stock.cantidad_actual, 0)

    def test_cliente_no_puede_cambiarse_rol_staff_ni_superuser_por_post(self):
        """Un usuario cliente no puede escalar privilegios mediante POST a su perfil."""
        self.client.force_login(self.cliente)
        response = self.client.post(
            reverse("usuarios:editar_perfil"),
            {
                "nombres": "Cliente",
                "apellidos": "Seguridad",
                "telefono": "3001234567",
                "email": "cliente_sec@test.com",
                # Ataque de escalamiento de privilegios
                "rol": "admin",
                "is_staff": "True",
                "is_superuser": "True",
                "estado": "inactivo",
            },
        )
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.rol, "cliente", "El rol no debe cambiar mediante POST")
        self.assertFalse(self.cliente.is_staff, "is_staff no debe cambiar mediante POST")
        self.assertFalse(self.cliente.is_superuser, "is_superuser no debe cambiar mediante POST")

    def test_comprobante_pago_se_guarda_con_nombre_uuid(self):
        """El nombre del comprobante almacenado debe usar uuid4().hex."""
        from apps.pagos.models import Pago, comprobante_upload_to
        pago = Pago(pedido=self.pedido)
        ruta = comprobante_upload_to(pago, "recibo_original_bancario.png")
        self.assertIn(f"comprobantes/pedido_{self.pedido.pk}/", ruta)
        self.assertNotIn("recibo_original_bancario", ruta, "No debe conservar el nombre original del cliente")
        self.assertTrue(ruta.endswith(".png"))

    def test_ataque_original_subtotal_negativo_rechazado_por_http(self):
        """Ataque original: inyección de subtotal negativo (-3500 sobre artículo de 26500).
        El backend debe rechazar la manipulación y no crear el pedido ni alterar montos."""
        material_cemento = MaterialConstruccion.objects.create(
            nombre="Cemento Gris Especial",
            unidad_medida=self.unidad,
            precio_referencia=Decimal("26500.00"),
        )
        self.client.force_login(self.cliente)
        # Ataque manipulando el payload HTTP para forzar subtotal o descuento anómalo
        response = self.client.post(
            reverse("clientes:crear_pedido"),
            {
                "material_id[]": [str(material_cemento.id)],
                "cantidad[]": ["1"],
                "ciudad": "Bogotá",
                "direccion_detalle": "Avenida 68 # 45-10",
                "descuento": "-3500.00",
                "subtotal": "-3500.00",
            },
        )
        # El backend ignora campos de subtotal inyectados por el cliente o rechaza
        # El pedido resultante debe calcularse estrictamente por el backend: 1 * 26500 = 26500
        ultimo_pedido = Pedido.objects.filter(usuario=self.cliente).order_by("-codigo_pedido").first()
        self.assertIsNotNone(ultimo_pedido)
        self.assertGreaterEqual(ultimo_pedido.total, Decimal("26500.00"))
        self.assertEqual(ultimo_pedido.descuento, Decimal("0.00"))
        self.assertNotEqual(ultimo_pedido.subtotal, Decimal("-3500.00"))

    def test_crear_pedido_con_cantidad_decimal_fraccionaria_m3(self):
        """Prueba de soporte de cantidades fraccionarias en m³ (ej. 2.50 m³ de Arena)."""
        unidad_m3 = UnidadMedida.objects.create(
            codigo="M3",
            nombre="Metro Cúbico",
            abreviatura="m3",
        )
        material_arena = MaterialConstruccion.objects.create(
            nombre="Arena Fina Especial",
            unidad_medida=unidad_m3,
            precio_referencia=Decimal("42000.00"),
        )
        Stock.objects.create(material=material_arena, cantidad_actual=Decimal("500.00"))
        self.client.force_login(self.cliente)
        response = self.client.post(
            reverse("clientes:crear_pedido"),
            {
                "material_id[]": [str(material_arena.id)],
                "cantidad[]": ["2.50"],
                "ciudad": "Bogotá",
                "direccion_detalle": "Calle 80 # 50-10",
            },
        )
        self.assertEqual(response.status_code, 302)
        pedido = Pedido.objects.filter(usuario=self.cliente).order_by("-codigo_pedido").first()
        self.assertIsNotNone(pedido)
        detalle = pedido.detalles.filter(material=material_arena).first()
        self.assertIsNotNone(detalle)
        self.assertEqual(detalle.cantidad, Decimal("2.50"))
        self.assertEqual(detalle.subtotal, Decimal("105000.00"))
        self.assertEqual(pedido.total, Decimal("105000.00"))

