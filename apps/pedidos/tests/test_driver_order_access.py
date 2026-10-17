from django.test import TestCase
from django.urls import reverse

from apps.logistica.models import Entrega
from apps.pedidos.models import Pedido
from apps.usuarios.models import Conductor, Usuario


class DriverOrderAccessTests(TestCase):
    def setUp(self):
        self.cliente = Usuario.objects.create_user(
            username="cliente-ruta@test.com",
            email="cliente-ruta@test.com",
            password="test-password",
            nombres="Cliente",
            apellidos="Ruta",
            documento="880001",
            tipo_documento="CC",
            rol="cliente",
        )
        self.conductor = Usuario.objects.create_user(
            username="conductor-asignado@test.com",
            email="conductor-asignado@test.com",
            password="test-password",
            nombres="Conductor",
            apellidos="Asignado",
            documento="880002",
            tipo_documento="CC",
            rol="conductor",
        )
        self.otro_conductor = Usuario.objects.create_user(
            username="otro-conductor@test.com",
            email="otro-conductor@test.com",
            password="test-password",
            nombres="Otro",
            apellidos="Conductor",
            documento="880003",
            tipo_documento="CC",
            rol="conductor",
        )
        self.perfil_conductor, _ = Conductor.ensure_for_user(self.conductor)
        self.pedido = Pedido.objects.create(
            usuario=self.cliente,
            conductor=self.perfil_conductor,
            estado=Pedido.VEHICULO_ASIGNADO,
            direccion_destino="Santa Marta, Magdalena, Colombia",
        )

    def test_conductor_asignado_puede_ver_pedido(self):
        self.client.force_login(self.conductor)

        response = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["orden"], self.pedido)
        self.assertTrue(response.context["puede_confirmar_entrega"])
        self.assertContains(response, "Confirmar Entrega")
        self.assertContains(response, "Observación (opcional)")

    def test_otro_conductor_no_puede_ver_pedido(self):
        self.client.force_login(self.otro_conductor)

        response = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )

        self.assertEqual(response.status_code, 403)

    def test_conductor_confirma_entrega_y_guarda_observacion(self):
        entrega = Entrega.objects.create(
            pedido=self.pedido,
            conductor=self.perfil_conductor,
            direccion_entrega=self.pedido.direccion_destino,
        )
        self.client.force_login(self.conductor)

        response = self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {
                "accion": "confirmar",
                "observacion": "Pedido entregado a la persona encargada.",
            },
        )

        self.assertRedirects(response, reverse("usuarios:panel"))
        self.pedido.refresh_from_db()
        entrega.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.ENTREGADO)
        self.assertIsNotNone(self.pedido.fecha_entrega_real)
        self.assertEqual(entrega.estado, "entregado")
        self.assertIsNotNone(entrega.fecha_entrega)
        novedad = entrega.novedades.get(tipo="observacion")
        self.assertEqual(
            novedad.descripcion,
            "Pedido entregado a la persona encargada.",
        )
        self.assertEqual(novedad.reportado_por, self.conductor)

        response = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )
        self.assertContains(response, "Pedido entregado a la persona encargada.")
