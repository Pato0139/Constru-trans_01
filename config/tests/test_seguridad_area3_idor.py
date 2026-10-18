"""
Pruebas de Seguridad: Mitigación de IDOR y Autorización por Objeto (Área 3)
Verifica que las consultas por ID filtren por propietario/permiso y devuelvan 404
(no 403 ni 200) ante intentos de acceso cruzado entre usuarios.
"""

from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.catalogo.models import MaterialConstruccion, UnidadMedida
from apps.ia.models import ConversationHistory, ConversationMessage
from apps.pagos.models import Factura, Pago
from apps.pedidos.models import Pedido
from apps.usuarios.models import Usuario


class SeguridadArea3IDORTests(TestCase):
    def setUp(self):
        self.unidad = UnidadMedida.objects.create(codigo="UND", nombre="Unidad")
        self.material = MaterialConstruccion.objects.create(
            nombre="Ladrillo Estructural",
            unidad_medida=self.unidad,
            precio_referencia=Decimal("2500.00"),
        )
        # Usuario Víctima (Usuario A)
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
        # Usuario Atacante (Usuario B)
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
        # Pedido del Usuario A
        self.pedido_a = Pedido.objects.create(
            usuario=self.usuario_a,
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
        # Conversación IA del Usuario A
        self.conv_a = ConversationHistory.objects.create(
            user=self.usuario_a,
        )
        self.msg_a = ConversationMessage.objects.create(
            conversation=self.conv_a,
            role="assistant",
            content="Información privada de su cotización",
        )

    def test_usuario_b_no_puede_ver_pago_de_usuario_a_devuelve_404(self):
        """Usuario B intenta ver el pago de Usuario A por URL y debe recibir 404 (no 403)."""
        self.client.force_login(self.usuario_b)
        response = self.client.get(reverse("pagos:detalle_pago", args=[self.pago_a.pk]))
        self.assertEqual(
            response.status_code,
            404,
            "El endpoint debe devolver 404 ante objetos ajenos para no revelar existencia (IDOR)",
        )

    def test_usuario_b_no_puede_descargar_comprobante_ajeno_devuelve_404(self):
        """Usuario B intenta descargar comprobante de pago de Usuario A y debe recibir 404."""
        self.client.force_login(self.usuario_b)
        response = self.client.get(reverse("pagos:ver_comprobante_pago", args=[self.pago_a.pk]))
        self.assertEqual(response.status_code, 404)

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
