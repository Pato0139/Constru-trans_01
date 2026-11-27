from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.logistica.models import Vehiculo
from apps.logistica.services import (
    asignar_conductor_y_vehiculo,
    confirmar_preparacion_e_iniciar_ruta,
    marcar_pedido_entregado,
    obtener_vehiculo_activo_conductor,
)
from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.pedidos.views import _obtener_recursos_transporte_para_pedido
from apps.usuarios.models import Conductor, Usuario


class VehiculoUnicoPorConductorTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="admin_veh_test",
            email="admin_veh@constru-trans.com",
            password="Password123!",
            nombres="Admin",
            apellidos="Test",
            documento="9900112233",
            tipo_documento="CC",
            rol="admin",
            is_staff=True,
        )
        self.cliente = Usuario.objects.create_user(
            username="cliente_veh_test",
            email="cliente_veh@constru-trans.com",
            password="Password123!",
            nombres="Cliente",
            apellidos="Test",
            documento="8800112233",
            tipo_documento="CC",
            rol="cliente",
        )
        self.zapata_user = Usuario.objects.create_user(
            username="zapata_test",
            email="zapata@constru-trans.com",
            password="Password123!",
            nombres="Andres",
            apellidos="Zapata",
            documento="1215545554",
            tipo_documento="CC",
            rol="conductor",
        )
        self.zapata_perfil, _ = Conductor.ensure_for_user(self.zapata_user)

        self.edward_user = Usuario.objects.create_user(
            username="edward_test",
            email="edward@constru-trans.com",
            password="Password123!",
            nombres="Edward",
            apellidos="Conduct",
            documento="1123456732",
            tipo_documento="CC",
            rol="conductor",
        )
        self.edward_perfil, _ = Conductor.ensure_for_user(self.edward_user)

        self.vehiculo_a = Vehiculo.objects.create(
            placa="CTV0357",
            tipo_vehiculo="Camion",
            marca="ConstruTrans",
            modelo="Modelo 14",
            capacidad_carga=Decimal("5.00"),
            estado="disponible",
        )
        self.vehiculo_b = Vehiculo.objects.create(
            placa="TR4620",
            tipo_vehiculo="Camion",
            marca="Foton",
            modelo="Aumark 2024",
            capacidad_carga=Decimal("5.00"),
            estado="disponible",
        )

    def _crear_pedido_autorizado(self):
        pedido = Pedido.objects.create(
            usuario=self.cliente,
            direccion_destino="Duitama Calle 10",
            subtotal=Decimal("100000.00"),
            total=Decimal("100000.00"),
            precio=Decimal("100000.00"),
            estado=Pedido.AUTORIZADO_DESPACHO,
        )
        Pago.objects.create(
            pedido=pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=Decimal("100000.00"),
            estado=Pago.APROBADO,
        )
        return pedido

    def test_conductor_solo_puede_usar_su_vehiculo_activo_hasta_terminar_entregas(self):
        pedido1 = self._crear_pedido_autorizado()
        pedido2 = self._crear_pedido_autorizado()
        pedido3 = self._crear_pedido_autorizado()

        # 1. Asignar pedido 1 a Zapata con vehículo A
        asignar_conductor_y_vehiculo(pedido1, self.zapata_user, self.vehiculo_a, usuario_admin=self.admin)

        # 2. Intentar asignar pedido 2 a Zapata con vehículo B (otro carro) -> BLOQUEADO
        with self.assertRaises(ValidationError) as ctx:
            asignar_conductor_y_vehiculo(pedido2, self.zapata_user, self.vehiculo_b, usuario_admin=self.admin)
        self.assertIn("CTV0357", str(ctx.exception))

        # 3. Intentar asignar pedido 2 a Edward con vehículo A (carro de Zapata) -> BLOQUEADO
        with self.assertRaises(ValidationError):
            asignar_conductor_y_vehiculo(pedido2, self.edward_user, self.vehiculo_a, usuario_admin=self.admin)

        # 4. Asignar pedido 2 a Zapata con su MISMO vehículo A -> PERMITIDO
        entrega2 = asignar_conductor_y_vehiculo(pedido2, self.zapata_user, self.vehiculo_a, usuario_admin=self.admin)
        self.assertEqual(entrega2.vehiculo_id, self.vehiculo_a.pk)

        # 5. En el selector de recursos para pedido 3:
        #    - Zapata tiene vehiculo_activo_id == vehiculo_a
        #    - vehiculo_a tiene conductor_activo_id == zapata_user.id
        #    - vehiculo_b tiene conductor_activo_id is None (libre)
        conductores, vehiculos = _obtener_recursos_transporte_para_pedido(pedido3)
        zapata_en_lista = next(c for c in conductores if c.id == self.zapata_user.id)
        edward_en_lista = next(c for c in conductores if c.id == self.edward_user.id)
        self.assertEqual(zapata_en_lista.vehiculo_activo_id, self.vehiculo_a.pk)
        self.assertIsNone(edward_en_lista.vehiculo_activo_id)

        veh_map = {v.pk: v for v in vehiculos}
        self.assertEqual(veh_map[self.vehiculo_a.pk].conductor_activo_id, self.zapata_user.id)
        self.assertIsNone(veh_map[self.vehiculo_b.pk].conductor_activo_id)

        # 6. Zapata entrega pedido 1 -> aún tiene pedido 2 activo, sigue atado a vehículo A
        confirmar_preparacion_e_iniciar_ruta(pedido1, self.zapata_user)
        marcar_pedido_entregado(pedido1, self.zapata_user)
        self.assertEqual(obtener_vehiculo_activo_conductor(self.zapata_perfil).pk, self.vehiculo_a.pk)

        with self.assertRaises(ValidationError):
            asignar_conductor_y_vehiculo(pedido3, self.zapata_user, self.vehiculo_b, usuario_admin=self.admin)

        # 7. Zapata entrega pedido 2 -> ya NO tiene entregas activas, vehículo A queda libre
        confirmar_preparacion_e_iniciar_ruta(pedido2, self.zapata_user)
        marcar_pedido_entregado(pedido2, self.zapata_user)
        self.assertIsNone(obtener_vehiculo_activo_conductor(self.zapata_perfil))

        self.vehiculo_a.refresh_from_db()
        self.assertEqual(self.vehiculo_a.estado, "disponible")

        # 8. Ahora Zapata puede recibir vehículo B y Edward puede recibir vehículo A
        entrega3 = asignar_conductor_y_vehiculo(pedido3, self.zapata_user, self.vehiculo_b, usuario_admin=self.admin)
        self.assertEqual(entrega3.vehiculo_id, self.vehiculo_b.pk)

        pedido4 = self._crear_pedido_autorizado()
        entrega4 = asignar_conductor_y_vehiculo(pedido4, self.edward_user, self.vehiculo_a, usuario_admin=self.admin)
        self.assertEqual(entrega4.vehiculo_id, self.vehiculo_a.pk)

