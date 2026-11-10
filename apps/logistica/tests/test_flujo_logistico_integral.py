from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.catalogo.models import MaterialConstruccion, Stock, UnidadMedida
from apps.clientes.models import Cliente
from apps.logistica.models import ConductorVehiculo, Entrega, Vehiculo
from apps.logistica.services import (
    asignar_conductor_y_vehiculo,
    autorizar_despacho_por_pago,
    confirmar_preparacion_e_iniciar_ruta,
    marcar_pedido_entregado,
)
from apps.pagos.models import Pago
from apps.pedidos.models import DetallePedido, Pedido
from apps.usuarios.models import Conductor, Notificacion, Usuario


class FlujoLogisticoIntegralTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.admin = Usuario.objects.create_user(
            username="admin_logistica",
            email="admin_logistica@construtrans.local",
            password="Password123!",
            nombres="Admin",
            apellidos="Logística",
            documento="9001001",
            tipo_documento="CC",
            rol="admin",
            estado="activo",
        )

        self.cliente_user = Usuario.objects.create_user(
            username="cliente_logistica",
            email="cliente_logistica@construtrans.local",
            password="Password123!",
            nombres="Constructora",
            apellidos="Del Norte",
            documento="9001002",
            tipo_documento="NIT",
            telefono="3005551122",
            rol="cliente",
            estado="activo",
        )
        self.cliente, _ = Cliente.ensure_for_user(self.cliente_user)

        self.otro_cliente_user = Usuario.objects.create_user(
            username="otro_cliente_logistica",
            email="otro_cliente@construtrans.local",
            password="Password123!",
            nombres="Ferretería",
            apellidos="Del Sur",
            documento="9001003",
            tipo_documento="NIT",
            rol="cliente",
            estado="activo",
        )
        self.otro_cliente, _ = Cliente.ensure_for_user(self.otro_cliente_user)

        self.conductor_user = Usuario.objects.create_user(
            username="conductor_activo",
            email="conductor_activo@construtrans.local",
            password="Password123!",
            nombres="Carlos",
            apellidos="Chofer",
            documento="9001004",
            tipo_documento="CC",
            telefono="3104445566",
            rol="conductor",
            estado="activo",
        )
        self.conductor_perfil, _ = Conductor.ensure_for_user(self.conductor_user)
        self.conductor_perfil.estado = "activo"
        self.conductor_perfil.save()

        self.otro_conductor_user = Usuario.objects.create_user(
            username="otro_conductor_activo",
            email="otro_conductor@construtrans.local",
            password="Password123!",
            nombres="Pedro",
            apellidos="Trans",
            documento="9001005",
            tipo_documento="CC",
            rol="conductor",
            estado="activo",
        )
        self.otro_conductor_perfil, _ = Conductor.ensure_for_user(self.otro_conductor_user)
        self.otro_conductor_perfil.estado = "activo"
        self.otro_conductor_perfil.save()

        self.conductor_inactivo_user = Usuario.objects.create_user(
            username="conductor_inactivo",
            email="conductor_inactivo@construtrans.local",
            password="Password123!",
            nombres="Luis",
            apellidos="Inactivo",
            documento="9001006",
            tipo_documento="CC",
            rol="conductor",
            estado="inactivo",
            is_active=False,
        )
        self.conductor_inactivo_perfil, _ = Conductor.ensure_for_user(self.conductor_inactivo_user)
        self.conductor_inactivo_perfil.estado = "inactivo"
        self.conductor_inactivo_perfil.save()

        self.vehiculo_disponible = Vehiculo.objects.create(
            placa="ABC123",
            marca="Chevrolet",
            modelo="NPR",
            tipo_vehiculo="Camión",
            capacidad_carga=Decimal("5.00"),
            estado="disponible",
        )
        self.vehiculo_ocupado = Vehiculo.objects.create(
            placa="XYZ789",
            marca="Hino",
            modelo="Dutro",
            tipo_vehiculo="Volqueta",
            capacidad_carga=Decimal("8.00"),
            estado="en_ruta",
        )

        self.unidad, _ = UnidadMedida.objects.get_or_create(
            codigo="BUL",
            defaults={"nombre": "Bulto", "abreviatura": "bulto"},
        )
        self.material = MaterialConstruccion.objects.create(
            nombre="Cemento Estructural 50kg",
            descripcion="Cemento gris de alta resistencia",
            precio_referencia=Decimal("32000.00"),
            unidad_medida=self.unidad,
        )
        Stock.objects.create(material=self.material, cantidad_actual=500)

        self.pedido = Pedido.objects.create(
            usuario=self.cliente_user,
            cliente=self.cliente,
            direccion_origen="Bodega Central",
            direccion_destino="Bogotá Calle 100 # 15-20",
            estado=Pedido.PENDIENTE,
        )
        DetallePedido.objects.create(
            pedido=self.pedido,
            material=self.material,
            cantidad=10,
            precio_unitario=Decimal("32000.00"),
            subtotal=Decimal("320000.00"),
        )
        self.pedido.calcular_total()

        self.pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=Decimal("320000.00"),
            estado=Pago.PENDIENTE,
        )

    def test_flujo_completo_end_to_end_con_notificaciones_y_liberacion(self):
        """
        Verifica el flujo completo:
        1. Admin aprueba pago -> Envío creado en «Autorizado Despacho» + notificaciones.
        2. Pedido aparece en el apartado Envíos del administrador.
        3. Admin asigna conductor y vehículo -> «Vehículo Asignado» + notificaciones.
        4. Conductor ve el pedido en su panel y consulta materiales/cantidades.
        5. Conductor confirma preparación e inicia ruta -> «En Ruta» + notificaciones.
        6. Conductor marca como entregado -> «Entregado» + notificaciones + liberación de vehículo y conductor.
        """
        # 1. Admin aprueba pago
        self.client.force_login(self.admin)
        resp_pago = self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[self.pago.pk]),
            {"accion": "aprobar", "observaciones": "Pago verificado correctamente."},
        )
        self.assertEqual(resp_pago.status_code, 302)

        self.pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.pago.estado, Pago.APROBADO)
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

        envios = Entrega.objects.filter(pedido=self.pedido)
        self.assertEqual(envios.count(), 1)
        entrega = envios.first()
        self.assertIsNone(entrega.conductor)
        self.assertEqual(entrega.estado, "pendiente")

        # Verificar notificaciones de pago aprobado (1 para cliente, 1 para admin)
        self.assertEqual(
            Notificacion.objects.filter(
                usuario=self.cliente_user,
                titulo=f"Pago aprobado - Pedido #CT-{self.pedido.codigo_pedido}",
            ).count(),
            1,
        )
        self.assertEqual(
            Notificacion.objects.filter(
                usuario=self.admin,
                titulo=f"Despacho autorizado - Pedido #CT-{self.pedido.codigo_pedido}",
            ).count(),
            1,
        )

        # 2. Pedido aparece en el apartado Envíos del administrador
        resp_envios = self.client.get(reverse("pedidos:lista_entregas_admin"))
        self.assertEqual(resp_envios.status_code, 200)
        self.assertContains(resp_envios, f"#CT-{self.pedido.codigo_pedido}")
        self.assertContains(resp_envios, "Autorizado Despacho")

        # 3. Admin asigna conductor y vehículo
        resp_asig = self.client.post(
            reverse("pedidos:crear_entrega", args=[self.pedido.codigo_pedido]),
            {
                "conductor": self.conductor_user.pk,
                "vehiculo": self.vehiculo_disponible.pk,
            },
        )
        self.assertRedirects(resp_asig, reverse("pedidos:lista_entregas_admin"))

        self.pedido.refresh_from_db()
        entrega.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.VEHICULO_ASIGNADO)
        self.assertEqual(Entrega.objects.filter(pedido=self.pedido).count(), 1)
        self.assertEqual(entrega.conductor, self.conductor_perfil)
        self.assertEqual(entrega.vehiculo, self.vehiculo_disponible)
        self.assertIsNotNone(entrega.fecha_asignacion)

        # Verificar notificaciones de asignación (cliente y admin)
        self.assertEqual(
            Notificacion.objects.filter(
                usuario=self.cliente_user,
                titulo=f"Conductor y vehículo asignados - Pedido #CT-{self.pedido.codigo_pedido}",
            ).count(),
            1,
        )
        self.assertEqual(
            Notificacion.objects.filter(
                usuario=self.admin,
                titulo=f"Asignación logística registrada - Pedido #CT-{self.pedido.codigo_pedido}",
            ).count(),
            1,
        )

        # 4. Conductor visualiza sus entregas y el detalle de materiales a recoger/cargar
        self.client.force_login(self.conductor_user)
        resp_panel_cond = self.client.get(reverse("usuarios:pedidos_conductor"))
        self.assertEqual(resp_panel_cond.status_code, 200)
        self.assertContains(resp_panel_cond, f"#CT-{self.pedido.codigo_pedido}")
        self.assertContains(resp_panel_cond, "Constructora Del Norte")
        self.assertContains(resp_panel_cond, "3005551122")
        self.assertContains(resp_panel_cond, "ABC123")
        self.assertContains(resp_panel_cond, "Vehículo Asignado")
        self.assertContains(resp_panel_cond, "Confirmar preparación e iniciar ruta")

        resp_det_cond = self.client.get(
            reverse("usuarios:detalle_entrega_conductor", args=[entrega.id_entrega])
        )
        self.assertEqual(resp_det_cond.status_code, 200)
        self.assertContains(resp_det_cond, "Cemento Estructural 50kg")
        self.assertContains(resp_det_cond, "10")
        self.assertContains(resp_det_cond, "Confirmar preparación e iniciar ruta")

        # 5. Conductor confirma preparación e inicia ruta
        resp_iniciar = self.client.post(
            reverse("usuarios:iniciar_entrega", args=[entrega.id_entrega])
        )
        self.assertEqual(resp_iniciar.status_code, 302)

        self.pedido.refresh_from_db()
        entrega.refresh_from_db()
        self.vehiculo_disponible.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.EN_RUTA)
        self.assertEqual(entrega.estado, "en_ruta")
        self.assertIsNotNone(entrega.fecha_salida)
        self.assertIsNotNone(self.pedido.fecha_toma_entrega)
        self.assertEqual(entrega.confirmado_salida_por, self.conductor_user)
        self.assertEqual(self.vehiculo_disponible.estado, "en_ruta")

        # Verificar notificaciones de inicio de ruta (cliente y admin)
        self.assertEqual(
            Notificacion.objects.filter(
                usuario=self.cliente_user,
                titulo=f"Pedido en ruta - Pedido #CT-{self.pedido.codigo_pedido}",
            ).count(),
            1,
        )
        self.assertEqual(
            Notificacion.objects.filter(
                usuario=self.admin,
                titulo=f"Inicio de ruta confirmado - Pedido #CT-{self.pedido.codigo_pedido}",
            ).count(),
            1,
        )

        # 6. Conductor marca el pedido como entregado
        resp_entregar = self.client.post(
            reverse("usuarios:finalizar_entrega", args=[entrega.id_entrega]),
            {"observaciones": "Recibido conforme en obra."},
        )
        self.assertEqual(resp_entregar.status_code, 302)

        self.pedido.refresh_from_db()
        entrega.refresh_from_db()
        self.vehiculo_disponible.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.ENTREGADO)
        self.assertEqual(entrega.estado, "entregado")
        self.assertIsNotNone(entrega.fecha_entrega)
        self.assertIsNotNone(self.pedido.fecha_entrega_real)
        self.assertEqual(entrega.entregado_por, self.conductor_user)
        self.assertEqual(self.vehiculo_disponible.estado, "disponible")
        self.assertFalse(
            ConductorVehiculo.objects.filter(
                conductor=self.conductor_perfil,
                fecha_fin__isnull=True,
            ).exists()
        )

        # Verificar notificaciones de entrega (cliente y admin)
        self.assertEqual(
            Notificacion.objects.filter(
                usuario=self.cliente_user,
                titulo=f"Pedido entregado - Pedido #CT-{self.pedido.codigo_pedido}",
            ).count(),
            1,
        )
        self.assertEqual(
            Notificacion.objects.filter(
                usuario=self.admin,
                titulo=f"Entrega completada - Pedido #CT-{self.pedido.codigo_pedido}",
            ).count(),
            1,
        )

    def test_aprobar_mismo_pago_dos_veces_no_duplica_envio_ni_notificaciones(self):
        self.client.force_login(self.admin)
        url = reverse("pagos:revisar_pago_pedido", args=[self.pago.pk])

        self.client.post(url, {"accion": "aprobar", "observaciones": "Primera aprobación"})
        self.client.post(url, {"accion": "aprobar", "observaciones": "Segunda aprobación"})
        # Llamada directa adicional al servicio para verificar idempotencia total
        autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)

        self.assertEqual(Entrega.objects.filter(pedido=self.pedido).count(), 1)
        self.assertEqual(
            Notificacion.objects.filter(
                usuario=self.cliente_user,
                titulo=f"Pago aprobado - Pedido #CT-{self.pedido.codigo_pedido}",
            ).count(),
            1,
        )
        self.assertEqual(
            Notificacion.objects.filter(
                usuario=self.admin,
                titulo=f"Despacho autorizado - Pedido #CT-{self.pedido.codigo_pedido}",
            ).count(),
            1,
        )

    def test_rechazar_pago_no_crea_envio(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[self.pago.pk]),
            {"accion": "rechazar", "observaciones": "Comprobante inválido."},
        )
        self.assertEqual(resp.status_code, 302)
        self.pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.pago.estado, Pago.RECHAZADO)
        self.assertEqual(self.pedido.estado, Pedido.PENDIENTE)
        self.assertFalse(Entrega.objects.filter(pedido=self.pedido).exists())

    def test_no_permite_asignar_conductor_inactivo_o_inexistente(self):
        autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)
        self.client.force_login(self.admin)

        # Conductor inactivo
        resp_inactivo = self.client.post(
            reverse("pedidos:crear_entrega", args=[self.pedido.codigo_pedido]),
            {
                "conductor": self.conductor_inactivo_user.pk,
                "vehiculo": self.vehiculo_disponible.pk,
            },
        )
        self.assertEqual(resp_inactivo.status_code, 400)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

        # Conductor inexistente
        resp_inexistente = self.client.post(
            reverse("pedidos:crear_entrega", args=[self.pedido.codigo_pedido]),
            {
                "conductor": 999999,
                "vehiculo": self.vehiculo_disponible.pk,
            },
        )
        self.assertEqual(resp_inexistente.status_code, 400)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

    def test_no_permite_asignar_vehiculo_ocupado(self):
        autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)
        self.client.force_login(self.admin)

        resp = self.client.post(
            reverse("pedidos:crear_entrega", args=[self.pedido.codigo_pedido]),
            {
                "conductor": self.conductor_user.pk,
                "vehiculo": self.vehiculo_ocupado.pk,
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

    def test_no_permite_iniciar_ruta_sin_asignacion(self):
        entrega = autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)

        with self.assertRaises(ValidationError):
            confirmar_preparacion_e_iniciar_ruta(entrega, self.admin)

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

    def test_no_permite_entregar_pedido_que_no_esta_en_ruta(self):
        autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)
        entrega = asignar_conductor_y_vehiculo(
            self.pedido,
            self.conductor_user.pk,
            self.vehiculo_disponible.pk,
            usuario_admin=self.admin,
        )

        # Intento por servicio
        with self.assertRaises(ValidationError):
            marcar_pedido_entregado(entrega, self.conductor_user)

        # Intento por vista POST
        self.client.force_login(self.conductor_user)
        resp = self.client.post(
            reverse("usuarios:finalizar_entrega", args=[entrega.id_entrega]),
            {"observaciones": "Intento sin estar en ruta"},
        )
        self.assertEqual(resp.status_code, 302)
        self.pedido.refresh_from_db()
        entrega.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.VEHICULO_ASIGNADO)
        self.assertEqual(entrega.estado, "pendiente")

    def test_conductor_no_puede_ver_ni_modificar_pedido_de_otro_conductor(self):
        autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)
        entrega = asignar_conductor_y_vehiculo(
            self.pedido,
            self.conductor_user.pk,
            self.vehiculo_disponible.pk,
            usuario_admin=self.admin,
        )

        self.client.force_login(self.otro_conductor_user)

        # No aparece en su listado de entregas
        resp_lista = self.client.get(reverse("usuarios:pedidos_conductor"))
        self.assertNotContains(resp_lista, f"#CT-{self.pedido.codigo_pedido}")

        # No puede ver detalle de entrega ajena
        resp_det_entrega = self.client.get(
            reverse("usuarios:detalle_entrega_conductor", args=[entrega.id_entrega])
        )
        self.assertEqual(resp_det_entrega.status_code, 403)

        # No puede ver detalle del pedido ajeno
        resp_det_pedido = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )
        self.assertEqual(resp_det_pedido.status_code, 403)

        # No puede iniciar ruta de entrega ajena
        resp_iniciar = self.client.post(
            reverse("usuarios:iniciar_entrega", args=[entrega.id_entrega])
        )
        self.assertEqual(resp_iniciar.status_code, 403)
        entrega.refresh_from_db()
        self.assertEqual(entrega.estado, "pendiente")

        # Poner en ruta con el conductor legítimo y probar que otro conductor no puede entregarlo
        confirmar_preparacion_e_iniciar_ruta(entrega, self.conductor_user)
        resp_finalizar = self.client.post(
            reverse("usuarios:finalizar_entrega", args=[entrega.id_entrega])
        )
        self.assertEqual(resp_finalizar.status_code, 403)
        entrega.refresh_from_db()
        self.assertEqual(entrega.estado, "en_ruta")

    def test_cliente_no_puede_acceder_a_envios_ni_pedidos_ajenos(self):
        self.client.force_login(self.otro_cliente_user)

        resp_det = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )
        self.assertEqual(resp_det.status_code, 403)

        resp_envios_admin = self.client.get(reverse("pedidos:lista_entregas_admin"))
        self.assertEqual(resp_envios_admin.status_code, 403)

    def test_acciones_cambio_estado_rechazan_get(self):
        autorizar_despacho_por_pago(self.pedido, usuario_admin=self.admin)
        entrega = asignar_conductor_y_vehiculo(
            self.pedido,
            self.conductor_user.pk,
            self.vehiculo_disponible.pk,
            usuario_admin=self.admin,
        )

        self.client.force_login(self.conductor_user)
        resp_get_iniciar = self.client.get(
            reverse("usuarios:iniciar_entrega", args=[entrega.id_entrega])
        )
        self.assertEqual(resp_get_iniciar.status_code, 405)

        resp_get_finalizar = self.client.get(
            reverse("usuarios:finalizar_entrega", args=[entrega.id_entrega])
        )
        self.assertEqual(resp_get_finalizar.status_code, 405)

        entrega.refresh_from_db()
        self.assertEqual(entrega.estado, "pendiente")

