"""
Pruebas de Seguridad: Mitigación de IDOR y Autorización por Objeto (Área 3)
Verifica que las consultas por ID filtren por propietario/permiso y devuelvan 404
(o 403 según corresponda) ante intentos de acceso cruzado entre usuarios A y B.
Cubre:
1. Pagos y comprobantes adjuntos.
2. Pedidos: ver, editar y anular/cancelar datos de otro usuario.
3. Facturación: descarga de PDF de facturas ajenas.
4. Logística y conductores: manipulación de entregas ajenas.
5. Catálogo, compras y vehículos: denegación de privilegios administrativos a clientes.
6. Asistente IA: manipulación de mensajes y feedback ajenos.
7. Escalamiento de privilegios: intento de modificación de rol, is_staff o estado por POST.
"""

from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.catalogo.models import MaterialConstruccion, UnidadMedida
from apps.clientes.models import Cliente
from apps.ia.models import ConversationHistory, ConversationMessage
from apps.logistica.models import Entrega, Vehiculo
from apps.pagos.models import Factura, Pago
from apps.pedidos.models import Pedido
from apps.usuarios.models import Conductor, Usuario


class SeguridadArea3IDORTests(TestCase):
    def setUp(self):
        self.unidad = UnidadMedida.objects.create(codigo="UND", nombre="Unidad")
        self.material = MaterialConstruccion.objects.create(
            nombre="Ladrillo Estructural",
            unidad_medida=self.unidad,
            precio_referencia=Decimal("2500.00"),
        )
        # Usuario Víctima (Usuario A - Cliente)
        self.usuario_a = Usuario.objects.create_user(
            username="victima_idor@test.com",
            email="victima_idor@test.com",
            password="Password123*",
            nombres="Víctima",
            apellidos="IDOR",
            documento="99001122",
            tipo_documento="CC",
            rol="cliente",
        )
        self.cliente_a, _ = Cliente.objects.get_or_create(
            usuario=self.usuario_a,
            defaults={"nombre_empresa": "Cliente A SAS"},
        )
        # Usuario Atacante (Usuario B - Cliente)
        self.usuario_b = Usuario.objects.create_user(
            username="atacante_idor@test.com",
            email="atacante_idor@test.com",
            password="Password123*",
            nombres="Atacante",
            apellidos="IDOR",
            documento="99001133",
            tipo_documento="CC",
            rol="cliente",
        )
        self.cliente_b, _ = Cliente.objects.get_or_create(
            usuario=self.usuario_b,
            defaults={"nombre_empresa": "Cliente B SAS"},
        )
        # Pedido del Usuario A
        self.pedido_a = Pedido.objects.create(
            usuario=self.usuario_a,
            cliente=self.cliente_a,
            direccion_destino="Calle 50 # 10-20, Tunja",
            estado=Pedido.PENDIENTE,
            total=Decimal("80000.00"),
        )
        # Pago del Usuario A con comprobante
        self.comprobante = SimpleUploadedFile(
            "comprobante_a.png",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82",
            content_type="image/png",
        )
        self.pago_a = Pago.objects.create(
            pedido=self.pedido_a,
            metodo=Pago.METODO_NEQUI,
            monto=Decimal("80000.00"),
            estado=Pago.PENDIENTE,
            comprobante=self.comprobante,
        )
        # Factura del Usuario A
        self.factura_a = Factura.objects.create(
            pedido=self.pedido_a,
            cliente=self.cliente_a,
            subtotal=Decimal("67226.89"),
            impuestos=Decimal("12773.11"),
            total=Decimal("80000.00"),
            estado=Factura.Estado.EMITIDA,
        )
        # Conversación IA del Usuario A
        self.conv_a = ConversationHistory.objects.create(
            user=self.usuario_a,
        )
        self.msg_a = ConversationMessage.objects.create(
            conversation=self.conv_a,
            role="assistant",
            content="Información privada de su cotización",
        )

        # Conductores C1 y C2
        self.u_conductor_1 = Usuario.objects.create_user(
            username="conductor1@test.com",
            email="conductor1@test.com",
            password="Password123*",
            nombres="Conductor",
            apellidos="Uno",
            documento="88001122",
            tipo_documento="CC",
            rol="conductor",
        )
        self.conductor_1, _ = Conductor.objects.get_or_create(
            usuario=self.u_conductor_1,
            defaults={"licencia_conduccion": "LIC-001", "categoria_licencia": "C2"},
        )
        self.u_conductor_2 = Usuario.objects.create_user(
            username="conductor2@test.com",
            email="conductor2@test.com",
            password="Password123*",
            nombres="Conductor",
            apellidos="Dos",
            documento="88001133",
            tipo_documento="CC",
            rol="conductor",
        )
        self.conductor_2, _ = Conductor.objects.get_or_create(
            usuario=self.u_conductor_2,
            defaults={"licencia_conduccion": "LIC-002", "categoria_licencia": "C2"},
        )
        self.vehiculo = Vehiculo.objects.create(
            placa="CTV-123",
            marca="Chevrolet",
            modelo="NKR",
            capacidad_carga=Decimal("3500.00"),
        )
        self.entrega_1 = Entrega.objects.create(
            pedido=self.pedido_a,
            conductor=self.conductor_1,
            vehiculo=self.vehiculo,
            direccion_entrega="Calle 50 # 10-20",
            estado="pendiente",
        )

    def test_usuario_b_no_puede_ver_pago_de_usuario_a_devuelve_404(self):
        """Usuario B intenta ver el pago de Usuario A por URL y debe recibir 404 (no 403)."""
        self.client.force_login(self.usuario_b)
        response = self.client.get(reverse("pagos:detalle_pago", args=[self.pago_a.pk]))
        self.assertEqual(
            response.status_code,
            404,
            "El endpoint debe devolver 404 ante pagos ajenos para no revelar existencia (IDOR)",
        )

    def test_usuario_b_no_puede_descargar_comprobante_ajeno_devuelve_404(self):
        """Usuario B intenta descargar comprobante de pago de Usuario A y debe recibir 404."""
        self.client.force_login(self.usuario_b)
        response = self.client.get(reverse("pagos:ver_comprobante_pago", args=[self.pago_a.pk]))
        self.assertEqual(response.status_code, 404)

    def test_usuario_b_no_puede_descargar_pdf_factura_ajena_devuelve_404(self):
        """Usuario B intenta descargar el PDF de la factura de Usuario A y recibe 404."""
        self.client.force_login(self.usuario_b)
        response = self.client.get(reverse("pagos:descargar_factura", args=[self.factura_a.pk]))
        self.assertEqual(
            response.status_code,
            404,
            "La descarga de PDF de factura ajena debe ser rechazada con 404",
        )

    def test_usuario_b_no_puede_ver_editar_ni_cancelar_pedido_de_a(self):
        """Usuario B intenta consultar, modificar o anular el pedido de Usuario A."""
        self.client.force_login(self.usuario_b)

        # 1. Intentar ver detalle del pedido ajeno en la vista de detalle
        r_ver = self.client.get(reverse("pedidos:ver_pedido_admin", args=[self.pedido_a.codigo_pedido]))
        self.assertIn(r_ver.status_code, [403, 404])

        # 2. Intentar editar el pedido ajeno
        r_edit = self.client.post(
            reverse("clientes:editar_pedido", args=[self.pedido_a.codigo_pedido]),
            {"direccion": "Calle Hacked # 666"},
        )
        self.assertIn(r_edit.status_code, [403, 404])

        # 3. Intentar anular/cancelar el pedido ajeno
        r_canc = self.client.post(
            reverse("clientes:cancelar_pedido", args=[self.pedido_a.codigo_pedido]),
            {"motivo": "Ataque IDOR"},
        )
        self.assertIn(r_canc.status_code, [403, 404])

        # Verificar que el pedido de A permanece inalterado
        self.pedido_a.refresh_from_db()
        self.assertEqual(self.pedido_a.estado, Pedido.PENDIENTE)
        self.assertEqual(self.pedido_a.direccion_destino, "Calle 50 # 10-20, Tunja")

    def test_conductor_2_no_puede_crear_novedad_sobre_entrega_de_conductor_1(self):
        """Conductor 2 intenta registrar novedad sobre la entrega asignada a Conductor 1 y es rechazado."""
        self.client.force_login(self.u_conductor_2)
        response = self.client.get(reverse("logistica:crear_novedad", args=[self.entrega_1.pk]))
        self.assertIn(response.status_code, [403, 404])

        response_post = self.client.post(
            reverse("logistica:crear_novedad", args=[self.entrega_1.pk]),
            {"tipo": "demora", "descripcion": "Intento no autorizado de novedad"},
        )
        self.assertIn(response_post.status_code, [403, 404])

    def test_cliente_no_puede_acceder_a_compras_ni_editar_vehiculo(self):
        """Un usuario con rol 'cliente' es rechazado al intentar acceder a módulos de compras o vehículos."""
        self.client.force_login(self.usuario_b)

        # Intento de ver lista de compras
        r_compras = self.client.get(reverse("compras:lista_compras"))
        self.assertIn(r_compras.status_code, [302, 403])

        # Intento de editar vehículo
        r_vehiculo = self.client.post(
            reverse("logistica:editar_vehiculo", args=[self.vehiculo.pk]),
            {"placa": "HCK-666", "marca": "Toyota", "modelo": "Hilux", "capacidad_carga": "5000"},
        )
        self.assertIn(r_vehiculo.status_code, [302, 403])

    def test_usuario_b_no_puede_escalar_rol_o_staff_en_editar_perfil(self):
        """Un cliente intenta auto-promoverse a 'admin' o 'is_staff=True' enviando campos en POST manual."""
        self.client.force_login(self.usuario_b)
        response = self.client.post(
            reverse("usuarios:editar_perfil"),
            {
                "nombres": "Atacante Escalado",
                "apellidos": "Hacker",
                "telefono": "3101234567",
                "rol": "admin",
                "is_staff": True,
                "is_superuser": True,
                "estado": "activo",
            },
        )
        self.usuario_b.refresh_from_db()
        self.assertEqual(self.usuario_b.rol, "cliente", "El rol no debe poder cambiarse desde perfil")
        self.assertFalse(self.usuario_b.is_staff, "is_staff no debe poder asignarse desde perfil")
        self.assertFalse(self.usuario_b.is_superuser, "is_superuser no debe poder asignarse desde perfil")

    def test_usuario_b_no_puede_enviar_feedback_a_mensaje_ia_ajeno(self):
        """Usuario B no puede manipular ni calificar mensajes de IA del Usuario A (IDOR en IA)."""
        self.client.force_login(self.usuario_b)
        response = self.client.post(
            reverse("feedback_ia"),
            data={"message_id": self.msg_a.id, "feedback": "negative", "comment": "Troll feedback"},
            content_type="application/json",
        )
        self.assertIn(
            response.status_code,
            [404, 400],
            "Debe rechazar feedback sobre mensajes ajenos",
        )
        data = response.json()
        self.assertFalse(data.get("success", False))

    def test_usuario_anonimo_es_redirigido_a_login_en_endpoints_protegidos(self):
        """Un usuario no autenticado debe ser redirigido a la pantalla de login."""
        endpoints = [
            reverse("pagos:detalle_pago", args=[self.pago_a.pk]),
            reverse("pagos:ver_comprobante_pago", args=[self.pago_a.pk]),
            reverse("clientes:panel_cliente"),
            reverse("clientes:mis_pedidos"),
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                302,
                f"URL {url} debe redirigir al login para anónimos",
            )
            self.assertIn(reverse("usuarios:login"), response.url)
