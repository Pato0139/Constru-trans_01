from decimal import Decimal

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from apps.catalogo.models import MaterialConstruccion, UnidadMedida
from apps.clientes.models import Cliente
from apps.logistica.models import Vehiculo
from apps.logistica.services import (
    asignar_conductor_y_vehiculo,
    autorizar_despacho_por_pago,
    confirmar_preparacion_e_iniciar_ruta,
)
from apps.pagos.models import Pago
from apps.pedidos.models import DetallePedido, Pedido
from apps.usuarios.models import Conductor, Usuario


class ControlMaestroBloqueoTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.admin = Usuario.objects.create_user(
            username="admin_cm",
            email="admin_cm@test.com",
            password="Password123!",
            nombres="Admin",
            apellidos="Maestro",
            documento="111222333",
            tipo_documento="CC",
            rol="admin",
            estado="activo",
        )

        self.cliente_user = Usuario.objects.create_user(
            username="cliente_cm",
            email="cliente_cm@test.com",
            password="Password123!",
            nombres="Cliente",
            apellidos="Test",
            documento="444555666",
            tipo_documento="CC",
            rol="cliente",
            estado="activo",
        )
        self.cliente, _ = Cliente.ensure_for_user(self.cliente_user)

        self.conductor_user = Usuario.objects.create_user(
            username="conductor_cm",
            email="conductor_cm@test.com",
            password="Password123!",
            nombres="Conductor",
            apellidos="Test",
            documento="777888999",
            tipo_documento="CC",
            rol="conductor",
            estado="activo",
        )
        self.conductor_perfil, _ = Conductor.ensure_for_user(self.conductor_user)
        self.conductor_perfil.estado = "activo"
        self.conductor_perfil.save()

        self.vehiculo = Vehiculo.objects.create(
            placa="XYZ987",
            marca="Foton",
            modelo="Aumark",
            tipo_vehiculo="Camión",
            capacidad_carga=Decimal("4.50"),
            estado="disponible",
        )

        self.unidad = UnidadMedida.objects.create(
            codigo="M3",
            nombre="Metro cúbico",
            abreviatura="m3",
        )
        self.material = MaterialConstruccion.objects.create(
            nombre="Gravilla",
            unidad_medida=self.unidad,
            descripcion="Gravilla común",
            precio_referencia=Decimal("60000.00"),
        )

        self.pedido = Pedido.objects.create(
            usuario=self.cliente_user,
            cliente=self.cliente,
            direccion_origen="Bodega Principal",
            direccion_destino="Tunja Calle 10 # 5-20",
            estado=Pedido.PENDIENTE,
        )
        DetallePedido.objects.create(
            pedido=self.pedido,
            material=self.material,
            cantidad=5,
            precio_unitario=Decimal("60000.00"),
            subtotal=Decimal("300000.00"),
        )
        self.pedido.calcular_total()

        self.pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=self.pedido.total,
            estado=Pago.APROBADO,
        )

    def test_control_maestro_bloqueado_en_frontend_cuando_vehiculo_asignado(self):
        """Al tener conductor y vehículo asignados, el Control Maestro se muestra deshabilitado en el HTML."""
        autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)
        asignar_conductor_y_vehiculo(
            self.pedido,
            self.conductor_user.pk,
            self.vehiculo.pk,
            usuario_admin=self.admin,
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

        self.client.force_login(self.admin)
        resp = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="order-master-state" name="estado" disabled')
        self.assertContains(resp, "Asignación Confirmada")
        self.assertContains(resp, "El pedido ya cuenta con conductor y vehículo asignados")

    def test_backend_rechaza_cambio_estado_control_maestro_cuando_vehiculo_asignado(self):
        """Si un usuario intenta enviar un POST al Control Maestro con un pedido asignado (bypass de DOM), el backend lo rechaza."""
        autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)
        asignar_conductor_y_vehiculo(
            self.pedido,
            self.conductor_user.pk,
            self.vehiculo.pk,
            usuario_admin=self.admin,
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

        self.client.force_login(self.admin)
        # Intenta forzar volver a 'pendiente' desde el form maestro
        resp = self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {"estado": "pendiente"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.pedido.refresh_from_db()
        # El estado NO debe haber cambiado
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

        # Verificar mensaje de error del backend
        mensajes = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertTrue(
            any("ya tiene conductor y vehículo asignados" in m for m in mensajes)
        )

    def test_backend_rechaza_crear_entrega_si_ya_esta_asignado(self):
        """No permite acceder ni enviar formulario de asignar entrega si ya cuenta con transporte asignado."""
        autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)
        asignar_conductor_y_vehiculo(
            self.pedido,
            self.conductor_user.pk,
            self.vehiculo.pk,
            usuario_admin=self.admin,
        )
        self.client.force_login(self.admin)

        # GET a crear_entrega debe redirigir
        resp_get = self.client.get(
            reverse("pedidos:crear_entrega", args=[self.pedido.codigo_pedido]),
            follow=True,
        )
        self.assertEqual(resp_get.status_code, 200)
        self.assertRedirects(
            resp_get,
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
        )

        mensajes = [m.message for m in get_messages(resp_get.wsgi_request)]
        self.assertTrue(
            any("ya cuenta con conductor y vehículo asignados" in m for m in mensajes)
        )

    def test_backend_rechaza_asignar_vehiculo_asignado_directamente_en_control_maestro(self):
        """No permite pasar a 'vehiculo_asignado' desde el Control Maestro sin asignar conductor y vehículo."""
        autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {"estado": "vehiculo_asignado"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

        mensajes = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertTrue(
            any("sin asignar un conductor y vehículo válidos" in m for m in mensajes)
        )

    def test_control_maestro_bloqueado_en_ruta(self):
        """En estado en_ruta el Control Maestro también permanece bloqueado en frontend y backend."""
        autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)
        entrega = asignar_conductor_y_vehiculo(
            self.pedido,
            self.conductor_user.pk,
            self.vehiculo.pk,
            usuario_admin=self.admin,
        )
        confirmar_preparacion_e_iniciar_ruta(entrega, self.conductor_user)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.EN_RUTA)

        self.client.force_login(self.admin)
        resp_get = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )
        self.assertContains(resp_get, 'id="order-master-state" name="estado" disabled')

        self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {"estado": "pendiente"},
            follow=True,
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.EN_RUTA)
