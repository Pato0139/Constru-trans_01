from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.logistica.models import Entrega, Vehiculo
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
        self.vehiculo = Vehiculo.objects.create(
            placa="CTV0336",
            marca="Chevrolet",
            modelo="NHR",
            tipo_vehiculo="Camión",
            capacidad_carga=Decimal("3.50"),
            estado="disponible",
        )
        self.pedido = Pedido.objects.create(
            usuario=self.cliente,
            conductor=self.perfil_conductor,
            estado=Pedido.VEHICULO_ASIGNADO,
            direccion_destino="Santa Marta, Magdalena, Colombia",
        )
        self.entrega = Entrega.objects.create(
            pedido=self.pedido,
            conductor=self.perfil_conductor,
            vehiculo=self.vehiculo,
            estado="pendiente",
            direccion_entrega=self.pedido.direccion_destino,
        )

    def test_conductor_asignado_puede_ver_pedido_e_iniciar_ruta(self):
        self.client.force_login(self.conductor)

        response = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["orden"], self.pedido)
        self.assertTrue(response.context["puede_iniciar_ruta"])
        self.assertFalse(response.context["puede_confirmar_entrega"])
        self.assertContains(response, "Confirmar preparación e iniciar ruta")

    def test_otro_conductor_no_puede_ver_pedido(self):
        self.client.force_login(self.otro_conductor)

        response = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )

        self.assertEqual(response.status_code, 403)

    def test_conductor_no_puede_marcar_entregado_sin_estar_en_ruta(self):
        self.client.force_login(self.conductor)

        response = self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {
                "accion": "confirmar",
                "observacion": "Intento prematuro sin iniciar ruta.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.pedido.refresh_from_db()
        self.entrega.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.VEHICULO_ASIGNADO)
        self.assertEqual(self.entrega.estado, "pendiente")

    def test_conductor_inicia_ruta_y_confirma_entrega_con_observacion(self):
        self.client.force_login(self.conductor)

        # Paso 1: Confirmar preparación e iniciar ruta
        resp_inicio = self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {"accion": "iniciar_ruta"},
        )
        self.assertRedirects(
            resp_inicio,
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
        )
        self.pedido.refresh_from_db()
        self.entrega.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.EN_RUTA)
        self.assertEqual(self.entrega.estado, "en_ruta")
        self.assertEqual(self.entrega.confirmado_salida_por, self.conductor)

        # Paso 2: Marcar como entregado
        response = self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {
                "accion": "confirmar",
                "observacion": "Pedido entregado a la persona encargada.",
            },
        )

        self.assertRedirects(response, reverse("usuarios:panel"))
        self.pedido.refresh_from_db()
        self.entrega.refresh_from_db()
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.ENTREGADO)
        self.assertIsNotNone(self.pedido.fecha_entrega_real)
        self.assertEqual(self.entrega.estado, "entregado")
        self.assertIsNotNone(self.entrega.fecha_entrega)
        self.assertEqual(self.entrega.entregado_por, self.conductor)
        self.assertEqual(self.vehiculo.estado, "disponible")

        novedad = self.entrega.novedades.get(tipo="observacion")
        self.assertEqual(
            novedad.descripcion,
            "Pedido entregado a la persona encargada.",
        )
        self.assertEqual(novedad.reportado_por, self.conductor)

        response = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )
        self.assertContains(response, "Pedido entregado a la persona encargada.")
