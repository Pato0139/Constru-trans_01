from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.catalogo.models import MaterialConstruccion, Stock, UnidadMedida
from apps.logistica.models import Entrega, Vehiculo
from apps.pagos.models import DetallePago, Pago
from apps.pedidos.models import DetallePedido, Pedido
from apps.usuarios.models import Conductor, Notificacion, Usuario

PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"


class FlujoPagosPedidosCancelacionesTests(TestCase):
    """Pruebas integrales de los 15 escenarios obligatorios de reestructuración."""

    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username="admin_flujo",
            email="admin_flujo@test.com",
            password="Password123!",
            nombres="Admin",
            apellidos="Principal",
            documento="10990001",
            tipo_documento="CC",
            rol="admin",
        )
        self.cliente = Usuario.objects.create_user(
            username="cliente_flujo",
            email="cliente_flujo@test.com",
            password="Password123!",
            nombres="Roberto",
            apellidos="Torres",
            documento="10990002",
            tipo_documento="CC",
            rol="cliente",
            telefono="3054789012",
        )
        self.conductor_user = Usuario.objects.create_user(
            username="conductor_flujo",
            email="conductor_flujo@test.com",
            password="Password123!",
            nombres="Carlos",
            apellidos="Ruta",
            documento="10990003",
            tipo_documento="CC",
            rol="conductor",
            estado="activo",
        )
        self.conductor, _ = Conductor.objects.update_or_create(
            usuario=self.conductor_user,
            defaults={"licencia": "LIC-9903", "estado": "activo"},
        )
        self.vehiculo = Vehiculo.objects.create(
            placa="FPC-123",
            marca="Chevrolet",
            modelo="NHR",
            tipo_vehiculo="Camión",
            capacidad_carga=Decimal("3.50"),
            estado="disponible",
        )

        self.unidad = UnidadMedida.objects.create(
            codigo="BUL",
            nombre="Bulto",
            abreviatura="bto",
        )
        self.material = MaterialConstruccion.objects.create(
            nombre="Cemento Gris 50kg",
            unidad_medida=self.unidad,
            descripcion="Cemento estructural",
            precio_referencia=Decimal("35000.00"),
        )
        self.stock, _ = Stock.objects.update_or_create(
            material=self.material,
            defaults={"cantidad_actual": 100},
        )

        self.pedido = Pedido.objects.create(
            usuario=self.cliente,
            cliente=self.cliente.perfil_cliente,
            direccion_origen="Bodega Central",
            direccion_destino="Tunja, Calle 20 # 10-15",
            estado=Pedido.PENDIENTE,
            total=Decimal("140000.00"),
            precio=Decimal("140000.00"),
        )
        self.detalle = DetallePedido.objects.create(
            pedido=self.pedido,
            material=self.material,
            cantidad=4,
            precio_unitario=Decimal("35000.00"),
        )
        # Reservamos las 4 unidades del stock (100 -> 96)
        self.stock.cantidad_actual = 96
        self.stock.save()

    def test_01_y_02_registro_pago_y_visualizacion_comprobante_detalle_sin_boton_volver(self):
        """1 y 2: Registro de pedido con comprobante y visualización en detalle sin botón Volver a Pagos."""
        self.client.force_login(self.cliente)
        comp = SimpleUploadedFile("soporte_bancolombia.png", PNG_BYTES, content_type="image/png")
        res = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_BANCOLOMBIA, "comprobante": comp},
        )
        self.assertEqual(res.status_code, 302)
        pago = Pago.objects.get(pedido=self.pedido)
        self.assertEqual(pago.estado, Pago.PENDIENTE)
        self.assertEqual(pago.monto, Decimal("140000.00"))
        self.assertEqual(pago.detalles.count(), 1)

        # Vista detalle como admin: debe mostrar Ver Pedido, vista previa/descarga, General / Otro motivo y NO mostrar Volver a Pagos
        self.client.force_login(self.admin)
        res_det = self.client.get(reverse("pagos:detalle_pago", args=[pago.pk]))
        self.assertEqual(res_det.status_code, 200)
        self.assertContains(res_det, "Ver Pedido")
        self.assertContains(res_det, "General / Otro motivo")
        self.assertNotContains(res_det, "Volver a Pagos")
        self.assertNotContains(res_det, "Volver a Mis Pagos")
        self.assertContains(res_det, "Abrir en tamaño completo")
        self.assertContains(res_det, "Descargar comprobante")

        # En el detalle del pedido solo debe estar Ver Detalle de Pago (sin Ir al Pago ni Revisar Pago redundantes)
        res_ped = self.client.get(reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]))
        self.assertContains(res_ped, "Ver Detalle de Pago")
        self.assertNotContains(res_ped, "Ir al Pago")
        self.assertNotContains(res_ped, "Revisar Pago")

        # Descarga del comprobante
        res_dl = self.client.get(reverse("pagos:ver_comprobante_pago", args=[pago.pk]) + "?download=1")
        self.assertEqual(res_dl.status_code, 200)
        self.assertIn("attachment;", res_dl["Content-Disposition"])

    def test_03_rechazo_pago_sin_motivo_debe_fallar(self):
        """3: Rechazo de pago sin motivo debe fallar y mantener el pago en estado pendiente."""
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_BANCOLOMBIA,
            monto=Decimal("140000.00"),
            estado=Pago.PENDIENTE,
        )
        self.client.force_login(self.admin)
        res = self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[pago.pk]),
            {"accion": "rechazar", "observaciones": "   "},
        )
        self.assertIn(res.status_code, (200, 302))
        pago.refresh_from_db()
        self.assertEqual(pago.estado, Pago.PENDIENTE)

    def test_04_y_05_rechazo_con_motivo_y_nuevo_envio_comprobante_conservando_historial(self):
        """4 y 5: Rechazo con motivo deja pedido en Pendiente de corrección (no cancela) y reenvío conserva intentos."""
        comp1 = SimpleUploadedFile("comprobante_intento1.png", PNG_BYTES, content_type="image/png")
        self.client.force_login(self.cliente)
        self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_BANCOLOMBIA, "comprobante": comp1},
        )
        pago = Pago.objects.get(pedido=self.pedido)

        # Admin rechaza diferenciando tipo_rechazo
        self.client.force_login(self.admin)
        res_rechazo = self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[pago.pk]),
            {
                "accion": "rechazar",
                "tipo_rechazo": "sin_comprobante",
                "observaciones": "Imagen en blanco, adjuntar recibo legible",
            },
        )
        self.assertEqual(res_rechazo.status_code, 302)
        pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(pago.estado, Pago.RECHAZADO)
        self.assertTrue(pago.requiere_correccion)
        self.assertEqual(self.pedido.estado, Pedido.PENDIENTE)
        self.assertTrue(self.pedido.requiere_correccion_pago)
        self.assertEqual(self.pedido.estado_gestion_display, "Pendiente de corrección de pago")
        self.assertIn("Ausencia de documentación", pago.observaciones)
        self.assertIn("Imagen en blanco", pago.observaciones)
        notif_rechazo = Notificacion.objects.filter(
            usuario=self.cliente,
            titulo__icontains=f"Pago rechazado en pedido #CT-{self.pedido.codigo_pedido}",
        ).first()
        self.assertIsNotNone(notif_rechazo)
        self.assertIn("12 horas", notif_rechazo.mensaje)

        # Cliente reenvía nuevo comprobante sin crear nuevo pedido ni borrar el archivo anterior
        self.client.force_login(self.cliente)
        comp2 = SimpleUploadedFile("comprobante_corregido2.png", PNG_BYTES, content_type="image/png")
        res_reenvio = self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_NEQUI, "comprobante": comp2},
        )
        self.assertEqual(res_reenvio.status_code, 302)
        pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(Pedido.objects.filter(usuario=self.cliente).count(), 1)
        self.assertEqual(pago.estado, Pago.PENDIENTE)
        self.assertFalse(self.pedido.requiere_correccion_pago)
        # Se conservan los eventos en DetallePago (intento 1 enviado, intento 1 rechazado, intento 2 reenviado)
        self.assertGreaterEqual(DetallePago.objects.filter(pago=pago).count(), 3)
        historial = pago.historial_intentos
        self.assertTrue(any(h.get("estado") == "rechazado" and h.get("comprobante") for h in historial))

    def test_06_y_07_aprobacion_posterior_y_paso_exclusivo_a_logistica_envios(self):
        """6 y 7: Solo los pedidos con pago aprobado pasan a Logística -> Envíos."""
        # Pedido con pago rechazado NO debe aparecer en Logística -> Envíos
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=Decimal("140000.00"),
            estado=Pago.RECHAZADO,
            observaciones="Falta verificación",
        )
        self.client.force_login(self.admin)
        res_envios_antes = self.client.get(reverse("pedidos:lista_entregas_admin"))
        self.assertEqual(res_envios_antes.status_code, 200)
        self.assertNotIn(self.pedido, res_envios_antes.context["pedidos"])

        # En Gestión de Pedidos sí aparece y puede filtrarse por pendiente_correccion_pago
        res_pedidos = self.client.get(
            reverse("pedidos:lista_pedidos_admin"),
            {"estado": "pendiente_correccion_pago"},
        )
        self.assertEqual(res_pedidos.status_code, 200)
        self.assertIn(self.pedido, res_pedidos.context["pedidos"])

        # En Gestión de Pagos puede filtrarse por requiere_correccion
        res_pagos = self.client.get(
            reverse("pagos:lista_pagos"),
            {"estado": Pago.REQUIERE_CORRECCION},
        )
        self.assertEqual(res_pagos.status_code, 200)
        self.assertIn(pago, res_pagos.context["pagos"])

        # Cliente corrige y admin aprueba
        pago.transicionar(Pago.PENDIENTE)
        pago.save()
        res_aprob = self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[pago.pk]),
            {"accion": "aprobar", "observaciones": "Verificado OK"},
        )
        self.assertEqual(res_aprob.status_code, 302)
        self.pedido.refresh_from_db()
        pago.refresh_from_db()
        self.assertEqual(pago.estado, Pago.APROBADO)
        self.assertFalse(pago.requiere_correccion)
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)
        self.assertTrue(Entrega.objects.filter(pedido=self.pedido).exists())

        # Ahora sí aparece en Logística -> Envíos
        res_envios_despues = self.client.get(reverse("pedidos:lista_entregas_admin"))
        self.assertIn(self.pedido, res_envios_despues.context["pedidos"])

    def test_08_09_10_11_modal_cancelacion_obligatorio_y_reversion_completa(self):
        """8, 9, 10 y 11: Detalle sin sección redundante inferior, cancelación sin motivo falla, con motivo cancela y revierte."""
        self.client.force_login(self.admin)
        res_det = self.client.get(reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]))
        self.assertEqual(res_det.status_code, 200)
        # Verifica que existe el modal único y NO el formulario redundante antiguo "Cancelar Envío / Pedido"
        self.assertContains(res_det, 'id="modalCancelarPedido"')
        self.assertContains(res_det, "¿Está seguro de cancelar este pedido?")
        self.assertNotContains(res_det, "Cancelar Envío / Pedido")

        # 9: Cancelación sin motivo debe fallar y dejar el pedido intacto
        res_sin_motivo = self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {"accion": "cancelar", "motivo": "   "},
        )
        self.assertEqual(res_sin_motivo.status_code, 302)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.PENDIENTE)

        # 10 y 11: Cancelación con motivo cambia estado, registra motivo, revierte stock y conserva pago
        comp = SimpleUploadedFile("comprobante_conservado.png", PNG_BYTES, content_type="image/png")
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_BANCOLOMBIA,
            monto=Decimal("140000.00"),
            estado=Pago.RECHAZADO,
            comprobante=comp,
            observaciones="Sin soporte válido",
        )
        res_con_motivo = self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {"accion": "cancelar", "motivo": "Cliente desistió de la compra tras rechazo de pago"},
        )
        self.assertEqual(res_con_motivo.status_code, 302)
        self.pedido.refresh_from_db()
        self.stock.refresh_from_db()
        pago.refresh_from_db()

        self.assertEqual(self.pedido.estado, Pedido.CANCELADO)
        self.assertEqual(self.stock.cantidad_actual, 100)  # 96 + 4 revertidos
        self.assertIn("Cliente desistió de la compra", self.pedido.motivo_cancelacion_display)
        # Se conservan el pedido, sus detalles y el pago con su comprobante
        self.assertEqual(self.pedido.detalles.count(), 1)
        self.assertTrue(bool(pago.comprobante))

        # Al consultar el detalle de un pedido cancelado, el selector de Control Maestro de Estado está deshabilitado
        res_det_cancelado = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )
        self.assertEqual(res_det_cancelado.status_code, 200)
        self.assertContains(
            res_det_cancelado,
            'id="order-master-state" name="estado" disabled',
        )
        self.assertContains(res_det_cancelado, "Estado Final Bloqueado")

    def test_12_y_13_pedido_cancelado_en_historial_y_excluido_de_logistica_envios(self):
        """12 y 13: Pedido cancelado va a Historial (admin y cliente) y NO aparece en Logística -> Envíos."""
        Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_CONTRAENTREGA,
            monto=Decimal("140000.00"),
            estado=Pago.APROBADO,
        )
        self.client.force_login(self.admin)
        # Autorizar y asignar conductor/vehículo primero
        self.pedido.estado = Pedido.AUTORIZADO_DESPACHO
        self.pedido.save(update_fields=["estado"])
        self.client.post(
            reverse("pedidos:crear_entrega", args=[self.pedido.codigo_pedido]),
            {"conductor": self.conductor_user.pk, "vehiculo": self.vehiculo.pk},
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.VEHICULO_ASIGNADO)

        # Cancelar pedido asignado
        self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {"accion": "cancelar", "motivo": "Obra suspendida por el cliente"},
        )
        self.pedido.refresh_from_db()
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.CANCELADO)
        self.assertEqual(self.vehiculo.estado, "disponible")

        # 13: No aparece en Logística -> Envíos ni en Gestión de Pedidos activos
        res_envios = self.client.get(reverse("pedidos:lista_entregas_admin"))
        self.assertNotIn(self.pedido, res_envios.context["pedidos"])
        res_activos = self.client.get(reverse("pedidos:lista_pedidos_admin"))
        self.assertNotIn(self.pedido, res_activos.context["pedidos"])

        # 12: Aparece en Historial de Pedidos de Admin y de Cliente
        res_hist_admin = self.client.get(
            reverse("pedidos:historial_pedidos_admin"),
            {"estado": "cancelado"},
        )
        self.assertEqual(res_hist_admin.status_code, 200)
        self.assertIn(self.pedido, res_hist_admin.context["pedidos"])
        self.assertContains(res_hist_admin, "Obra suspendida por el cliente")

        self.client.force_login(self.cliente)
        res_hist_cli = self.client.get(
            reverse("clientes:historial_pedidos"),
            {"estado": "cancelado"},
        )
        self.assertEqual(res_hist_cli.status_code, 200)
        self.assertIn(self.pedido, res_hist_cli.context["pedidos"])
        self.assertContains(res_hist_cli, "Obra suspendida por el cliente")

    def test_14_bloqueo_pedido_sin_productos_o_importe_cero(self):
        """14: No permitir que un pedido sin productos o con importe $0 sea aprobado ni autorizado para despacho."""
        pedido_vacio = Pedido.objects.create(
            usuario=self.cliente,
            cliente=self.cliente.perfil_cliente,
            direccion_origen="Bodega Central",
            direccion_destino="Duitama",
            estado=Pedido.PENDIENTE,
            total=Decimal("0.00"),
            precio=Decimal("0.00"),
        )
        pago_invalido = Pago.objects.create(
            pedido=pedido_vacio,
            metodo=Pago.METODO_BANCOLOMBIA,
            monto=Decimal("0.00"),
            estado=Pago.PENDIENTE,
        )
        self.client.force_login(self.admin)
        res = self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[pago_invalido.pk]),
            {"accion": "aprobar", "observaciones": "Intento aprobar pedido en 0"},
        )
        self.assertEqual(res.status_code, 302)
        pago_invalido.refresh_from_db()
        pedido_vacio.refresh_from_db()
        self.assertEqual(pago_invalido.estado, Pago.PENDIENTE)
        self.assertEqual(pedido_vacio.estado, Pedido.PENDIENTE)
        self.assertFalse(Entrega.objects.filter(pedido=pedido_vacio).exists())

        # Visualización del detalle de pago sin comprobante en Bancolombia dice "No se adjuntó comprobante"
        res_det = self.client.get(reverse("pagos:detalle_pago", args=[pago_invalido.pk]))
        self.assertContains(res_det, "No se adjuntó comprobante")
        self.assertNotContains(res_det, "No aplica (ej. contraentrega)")

    def test_15_flujo_completo_asignacion_ruta_y_entrega_final(self):
        """15: Flujo completo desde pago aprobado -> asignación -> en ruta -> entregado -> historial."""
        comp = SimpleUploadedFile("comprobante_ok.png", PNG_BYTES, content_type="image/png")
        self.client.force_login(self.cliente)
        self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_BANCOLOMBIA, "comprobante": comp},
        )
        pago = Pago.objects.get(pedido=self.pedido)

        # 1. Admin aprueba pago
        self.client.force_login(self.admin)
        self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[pago.pk]),
            {"accion": "aprobar", "observaciones": "Pago verificado"},
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.AUTORIZADO_DESPACHO)

        # 2. Admin asigna conductor y vehículo
        self.client.post(
            reverse("pedidos:crear_entrega", args=[self.pedido.codigo_pedido]),
            {"conductor": self.conductor_user.pk, "vehiculo": self.vehiculo.pk},
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.VEHICULO_ASIGNADO)

        # 3. Conductor confirma preparación e inicia ruta
        self.client.force_login(self.conductor_user)
        self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {"accion": "iniciar_ruta"},
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.EN_RUTA)

        # 4. Conductor confirma entrega
        self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {"accion": "confirmar", "observacion": "Recibido conforme en obra"},
        )
        self.pedido.refresh_from_db()
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.ENTREGADO)
        self.assertEqual(self.vehiculo.estado, "disponible")

        # 5. Aparece en Historial como Entregado
        self.client.force_login(self.admin)
        res_hist = self.client.get(
            reverse("pedidos:historial_pedidos_admin"),
            {"estado": "entregado"},
        )
        self.assertIn(self.pedido, res_hist.context["pedidos"])

    def test_16_cancelacion_automatica_al_vencer_plazo_12_horas_sin_corregir_pago(self):
        """16: Si pasan 12 horas tras el rechazo del pago sin corrección, el pedido se cancela automáticamente y va al historial."""
        comp1 = SimpleUploadedFile("comprobante_12h.png", PNG_BYTES, content_type="image/png")
        self.client.force_login(self.cliente)
        self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_BANCOLOMBIA, "comprobante": comp1},
        )
        pago = Pago.objects.get(pedido=self.pedido)

        self.client.force_login(self.admin)
        self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[pago.pk]),
            {"accion": "rechazar", "observaciones": "Comprobante borroso"},
        )
        pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.PENDIENTE)
        self.assertIsNotNone(pago.fecha_limite_correccion)
        self.assertFalse(pago.plazo_correccion_vencido)

        # Simulamos que transcurrieron 12 horas y 5 minutos desde la revisión
        Pago.objects.filter(pk=pago.pk).update(
            fecha_revision=timezone.now() - timedelta(hours=12, minutes=5)
        )
        pago.refresh_from_db()
        self.assertTrue(pago.plazo_correccion_vencido)

        # Al consultar o intentar corregir el pago vencido, el pedido se cancela automáticamente y revierte stock
        self.client.force_login(self.cliente)
        res_intento_tardio = self.client.get(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido])
        )
        self.assertEqual(res_intento_tardio.status_code, 302)
        self.pedido.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.CANCELADO)
        self.assertEqual(self.stock.cantidad_actual, 100)
        self.assertIn("12 horas", self.pedido.motivo_cancelacion_display)

        # El pedido aparece ahora en el Historial como Cancelado
        res_hist = self.client.get(reverse("clientes:historial_pedidos"), {"estado": "cancelado"})
        self.assertIn(self.pedido, res_hist.context["pedidos"])

    def test_17_cancelacion_automatica_en_segundo_rechazo_de_pago(self):
        """17: Si el cliente reenvía el comprobante mal y se rechaza por segunda vez, el pedido se cancela automáticamente y va al historial."""
        comp1 = SimpleUploadedFile("intento_mal_1.png", PNG_BYTES, content_type="image/png")
        self.client.force_login(self.cliente)
        self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_BANCOLOMBIA, "comprobante": comp1},
        )
        pago = Pago.objects.get(pedido=self.pedido)

        # Primer rechazo -> queda pendiente de corrección (con 12 horas)
        self.client.force_login(self.admin)
        self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[pago.pk]),
            {"accion": "rechazar", "observaciones": "Primer comprobante ilegible"},
        )
        pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(pago.total_rechazos, 1)
        self.assertEqual(self.pedido.estado, Pedido.PENDIENTE)
        self.assertTrue(self.pedido.requiere_correccion_pago)

        # Cliente reenvía segundo comprobante dentro del plazo
        self.client.force_login(self.cliente)
        comp2 = SimpleUploadedFile("intento_mal_2.png", PNG_BYTES, content_type="image/png")
        self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_BANCOLOMBIA, "comprobante": comp2},
        )

        # Admin rechaza por segunda vez -> el pedido se cancela automáticamente, revierte stock y va al historial
        self.client.force_login(self.admin)
        self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[pago.pk]),
            {"accion": "rechazar", "observaciones": "Segundo comprobante también inválido"},
        )
        pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.stock.refresh_from_db()

        self.assertEqual(pago.estado, Pago.RECHAZADO)
        self.assertEqual(pago.total_rechazos, 2)
        self.assertFalse(pago.requiere_correccion)
        self.assertEqual(self.pedido.estado, Pedido.CANCELADO)
        self.assertEqual(self.stock.cantidad_actual, 100)
        self.assertIn("segundo rechazo", self.pedido.motivo_cancelacion_display.lower())

        # Aparece en Historial de Pedidos de Admin y Cliente
        res_hist_adm = self.client.get(reverse("pedidos:historial_pedidos_admin"), {"estado": "cancelado"})
        self.assertIn(self.pedido, res_hist_adm.context["pedidos"])

    def test_18_asignar_conductor_vehiculo_desde_detalle_pedido_y_flujo_conductor(self):
        self.client.force_login(self.cliente)
        comp = SimpleUploadedFile("comprobante_asig.png", PNG_BYTES, content_type="image/png")
        self.client.post(
            reverse("pagos:registrar_pago_pedido", args=[self.pedido.codigo_pedido]),
            {"metodo": Pago.METODO_BANCOLOMBIA, "comprobante": comp},
        )
        pago = Pago.objects.get(pedido=self.pedido)
        self.client.force_login(self.admin)

        # 1. Mientras el pago está en revisión, la asignación desde el detalle está bloqueada
        res_det_pend = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )
        self.assertEqual(res_det_pend.status_code, 200)
        self.assertContains(res_det_pend, "Disponible al aprobar pago")
        self.assertNotContains(res_det_pend, 'id="select-conductor-detalle"')

        res_bloqueado = self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {
                "accion": "asignar_transporte",
                "conductor": self.conductor_user.pk,
                "vehiculo": self.vehiculo.pk,
            },
        )
        self.assertEqual(res_bloqueado.status_code, 302)
        self.pedido.refresh_from_db()
        self.assertIsNone(self.pedido.conductor_id)

        # 2. Aprobar el pago -> Se habilitan los selectores de conductor y vehículo en el detalle del pedido
        self.client.post(
            reverse("pagos:revisar_pago_pedido", args=[pago.pk]),
            {"accion": "aprobar"},
        )
        res_det_aprob = self.client.get(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido])
        )
        self.assertContains(res_det_aprob, 'id="select-conductor-detalle"')
        self.assertContains(res_det_aprob, 'id="select-vehiculo-detalle"')
        self.assertContains(res_det_aprob, 'id="btn-asignar-transporte-detalle"')

        # 3. Admin asigna conductor y vehículo directamente desde el apartado de Asignación de Transporte
        res_asig = self.client.post(
            reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]),
            {
                "accion": "asignar_transporte",
                "conductor": self.conductor_user.pk,
                "vehiculo": self.vehiculo.pk,
            },
        )
        self.assertEqual(res_asig.status_code, 302)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.VEHICULO_ASIGNADO)
        entrega = self.pedido.envio_actual
        self.assertIsNotNone(entrega)
        self.assertEqual(entrega.conductor_id, self.conductor.pk)
        self.assertEqual(entrega.vehiculo_id, self.vehiculo.pk)

        # 4. El conductor asignado recibe el pedido en su panel y puede cambiarlo a En Ruta y Entregado
        self.client.force_login(self.conductor_user)
        res_panel_cond = self.client.get(reverse("usuarios:panel_conductor"))
        self.assertEqual(res_panel_cond.status_code, 200)
        self.assertIn(entrega, list(res_panel_cond.context["entregas"]))

        # Conductor confirma preparación e inicia ruta -> En Ruta
        res_ruta = self.client.post(reverse("usuarios:iniciar_entrega", args=[entrega.id_entrega]))
        self.assertEqual(res_ruta.status_code, 302)
        self.pedido.refresh_from_db()
        entrega.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.EN_RUTA)
        self.assertEqual(entrega.estado, "en_ruta")

        # Conductor marca como entregado -> Entregado
        res_ent = self.client.post(
            reverse("usuarios:finalizar_entrega", args=[entrega.id_entrega]),
            {"observacion": "Entregado en obra sin novedad"},
        )
        self.assertEqual(res_ent.status_code, 302)
        self.pedido.refresh_from_db()
        entrega.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.ENTREGADO)
        self.assertEqual(entrega.estado, "entregado")


