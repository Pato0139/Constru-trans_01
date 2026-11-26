from datetime import timedelta
from decimal import Decimal
from io import BytesIO
import tempfile
from unittest.mock import patch

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Historial
from apps.logistica.models import ConductorVehiculo, Entrega, Vehiculo
from apps.pedidos.models import Pedido
from apps.usuarios.models import Conductor, Notificacion, Usuario


class ImprevistosLogisticosTests(TestCase):
    def setUp(self):
        self.admin = self._user("admin-imprevistos", "admin", "Admin")
        self.cliente = self._user("cliente-imprevistos", "cliente", "Cliente")
        self.conductor_user = self._user("conductor-imprevistos", "conductor", "Conductor")
        self.conductor_alt_user = self._user("conductor-alt", "conductor", "Alterno")
        self.conductor = Conductor.ensure_for_user(self.conductor_user)[0]
        self.conductor_alt = Conductor.ensure_for_user(self.conductor_alt_user)[0]
        self.vehiculo = self._vehicle("CTV7101")
        self.vehiculo_alt = self._vehicle("CTV7102")
        self.pedido = Pedido.objects.create(
            usuario=self.cliente,
            estado=Pedido.VEHICULO_ASIGNADO,
            total=Decimal("100000.00"),
            subtotal=Decimal("100000.00"),
            direccion_destino="Barranquilla, Colombia",
            fecha_entrega_programada=timezone.now() + timedelta(days=3),
        )
        self.entrega = Entrega.objects.create(
            pedido=self.pedido,
            conductor=self.conductor,
            vehiculo=self.vehiculo,
            estado="pendiente",
            direccion_entrega=self.pedido.direccion_destino,
        )
        self.client.force_login(self.admin)

    def _user(self, username, rol, name):
        return Usuario.objects.create_user(
            username=username,
            email=f"{username}@test.com",
            password="test-password",
            nombres=name,
            apellidos="Prueba",
            documento=f"DOC-{username}",
            tipo_documento="CC",
            rol=rol,
        )

    def _vehicle(self, plate):
        return Vehiculo.objects.create(
            placa=plate,
            marca="Chevrolet",
            modelo="NHR",
            tipo_vehiculo="Camión",
            capacidad_carga=Decimal("5.50"),
            estado="disponible",
        )

    def _reassign(self, **data):
        return self.client.post(
            reverse("logistica:reasignar_entrega", args=[self.pedido.codigo_pedido]),
            {"motivo": "operativo", **data},
        )

    def test_reasigna_solo_conductor_y_conserva_vehiculo(self):
        response = self._reassign(conductor=self.conductor_alt.pk)
        self.assertEqual(response.status_code, 302)
        self.entrega.refresh_from_db()
        self.assertEqual(self.entrega.conductor_id, self.conductor_alt.pk)
        self.assertEqual(self.entrega.vehiculo_id, self.vehiculo.pk)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.VEHICULO_ASIGNADO)

    def test_reasigna_solo_vehiculo_y_conserva_conductor(self):
        response = self._reassign(vehiculo=self.vehiculo_alt.pk)
        self.assertEqual(response.status_code, 302)
        self.entrega.refresh_from_db()
        self.assertEqual(self.entrega.conductor_id, self.conductor.pk)
        self.assertEqual(self.entrega.vehiculo_id, self.vehiculo_alt.pk)

    def test_reasigna_ambos_recursos_y_guarda_bitacora(self):
        response = self._reassign(conductor=self.conductor_alt.pk, vehiculo=self.vehiculo_alt.pk)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Historial.objects.filter(
                modulo="pedido", elemento_id=str(self.pedido.codigo_pedido), descripcion__icontains="Reasignación logística"
            ).exists()
        )
        self.assertTrue(Notificacion.objects.filter(usuario=self.cliente, titulo__startswith="Actualización logística").exists())

    def test_permite_reasignar_a_conductor_con_otro_envio_y_conserva_el_otro_pedido(self):
        pedido_otro = Pedido.objects.create(usuario=self.cliente, estado=Pedido.VEHICULO_ASIGNADO)
        entrega_otra = Entrega.objects.create(
            pedido=pedido_otro,
            conductor=self.conductor_alt,
            vehiculo=self.vehiculo_alt,
            estado="pendiente",
            direccion_entrega="Santa Marta, Colombia",
        )
        response = self._reassign(conductor=self.conductor_alt.pk)
        self.assertEqual(response.status_code, 302)
        self.entrega.refresh_from_db()
        entrega_otra.refresh_from_db()
        self.assertEqual(self.entrega.conductor_id, self.conductor_alt.pk)
        self.assertEqual(self.entrega.vehiculo_id, self.vehiculo.pk)
        self.assertEqual(entrega_otra.conductor_id, self.conductor_alt.pk)
        self.assertEqual(entrega_otra.vehiculo_id, self.vehiculo_alt.pk)

    def test_reasignar_no_cierra_el_vehiculo_que_el_nuevo_conductor_usa_en_otro_pedido(self):
        asignacion_actual = ConductorVehiculo.objects.create(
            conductor=self.conductor, vehiculo=self.vehiculo
        )
        asignacion_otro_pedido = ConductorVehiculo.objects.create(
            conductor=self.conductor_alt, vehiculo=self.vehiculo_alt
        )
        pedido_otro = Pedido.objects.create(usuario=self.cliente, estado=Pedido.VEHICULO_ASIGNADO)
        entrega_otra = Entrega.objects.create(
            pedido=pedido_otro,
            conductor=self.conductor_alt,
            vehiculo=self.vehiculo_alt,
            estado="pendiente",
            direccion_entrega="Santa Marta, Colombia",
        )

        response = self._reassign(conductor=self.conductor_alt.pk)

        self.assertEqual(response.status_code, 302)
        asignacion_actual.refresh_from_db()
        asignacion_otro_pedido.refresh_from_db()
        entrega_otra.refresh_from_db()
        self.assertIsNotNone(asignacion_actual.fecha_fin)
        self.assertIsNone(asignacion_otro_pedido.fecha_fin)
        self.assertEqual(entrega_otra.vehiculo_id, self.vehiculo_alt.pk)
        self.assertTrue(
            ConductorVehiculo.objects.filter(
                conductor=self.conductor_alt,
                vehiculo=self.vehiculo,
                fecha_fin__isnull=True,
            ).exists()
        )

    def test_reasignacion_rechaza_vehiculo_asignado_a_otro_conductor_aunque_diga_disponible(self):
        asignacion = ConductorVehiculo.objects.create(
            conductor=self.conductor_alt, vehiculo=self.vehiculo_alt
        )

        response = self._reassign(vehiculo=self.vehiculo_alt.pk)

        self.assertEqual(response.status_code, 200)
        self.entrega.refresh_from_db()
        asignacion.refresh_from_db()
        self.assertEqual(self.entrega.vehiculo_id, self.vehiculo.pk)
        self.assertIsNone(asignacion.fecha_fin)

    def test_rechaza_vehiculo_fuera_de_servicio_y_no_cambia_asignacion(self):
        self.vehiculo_alt.estado = "mantenimiento"
        self.vehiculo_alt.save(update_fields=["estado"])
        response = self._reassign(vehiculo=self.vehiculo_alt.pk)
        self.assertEqual(response.status_code, 200)
        self.entrega.refresh_from_db()
        self.assertEqual(self.entrega.vehiculo_id, self.vehiculo.pk)

    def test_reasignacion_en_ruta_conserva_estado_y_libera_vehiculo_anterior(self):
        self.pedido.transicionar(Pedido.EN_RUTA)
        self.pedido.save(update_fields=["estado"])
        self.entrega.estado = "en_ruta"
        self.entrega.save(update_fields=["estado"])
        self.vehiculo.estado = "en_ruta"
        self.vehiculo.save(update_fields=["estado"])

        response = self._reassign(vehiculo=self.vehiculo_alt.pk)
        self.assertEqual(response.status_code, 302)
        self.pedido.refresh_from_db()
        self.entrega.refresh_from_db()
        self.vehiculo.refresh_from_db()
        self.vehiculo_alt.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.EN_RUTA)
        self.assertEqual(self.entrega.estado, "en_ruta")
        self.assertEqual(self.vehiculo.estado, "disponible")
        self.assertEqual(self.vehiculo_alt.estado, "en_ruta")

    def test_reasignacion_solo_administrador(self):
        self.client.force_login(self.conductor_user)
        response = self.client.get(reverse("logistica:reasignar_entrega", args=[self.pedido.pk]))
        self.assertEqual(response.status_code, 403)

    def test_reagendar_conserva_estado_y_notifica_cliente(self):
        anterior = timezone.localtime(self.pedido.fecha_entrega_programada).replace(second=0, microsecond=0)
        nueva = timezone.localtime(timezone.now() + timedelta(days=5)).replace(second=0, microsecond=0)
        response = self.client.post(
            reverse("logistica:reagendar_entrega", args=[self.pedido.codigo_pedido]),
            {
                "fecha_entrega_programada": nueva.strftime("%Y-%m-%dT%H:%M"),
                "motivo": "clima",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.VEHICULO_ASIGNADO)
        self.assertEqual(timezone.localtime(self.pedido.fecha_entrega_programada), nueva)
        historial = Historial.objects.filter(
            modulo="pedido",
            elemento_id=str(self.pedido.codigo_pedido),
            descripcion__icontains="Entrega reagendada",
        )
        self.assertTrue(historial.exists())
        self.assertIn(anterior.strftime("%d/%m/%Y %H:%M"), historial.first().descripcion)
        notificacion = Notificacion.objects.get(
            usuario=self.cliente,
            titulo__startswith="Nueva fecha de entrega",
        )
        self.assertIn(anterior.strftime("%d/%m/%Y %H:%M"), notificacion.mensaje)
        self.assertIn(nueva.strftime("%d/%m/%Y %H:%M"), notificacion.mensaje)
        self.assertIn("Condiciones climáticas desfavorables", notificacion.mensaje)
        self.assertFalse(Notificacion.objects.filter(usuario=self.conductor_user).exists())
        self.assertFalse(Notificacion.objects.filter(usuario=self.admin).exists())

    def test_reagendamiento_individual_no_cambia_otros_pedidos_del_conductor(self):
        otra_fecha = timezone.localtime(timezone.now() + timedelta(days=8)).replace(second=0, microsecond=0)
        otra_programacion = Pedido.objects.create(
            usuario=self.cliente,
            estado=Pedido.VEHICULO_ASIGNADO,
            total=Decimal("200000.00"),
            subtotal=Decimal("200000.00"),
            direccion_destino="Santa Marta, Colombia",
            fecha_entrega_programada=otra_fecha,
        )
        otra_entrega = Entrega.objects.create(
            pedido=otra_programacion,
            conductor=self.conductor,
            vehiculo=self.vehiculo_alt,
            estado="pendiente",
            direccion_entrega=otra_programacion.direccion_destino,
        )
        fecha_seleccionada = timezone.localtime(timezone.now() + timedelta(days=4)).replace(second=0, microsecond=0)

        response = self.client.post(
            reverse("logistica:reagendar_entrega", args=[self.pedido.codigo_pedido]),
            {
                "fecha_entrega_programada": fecha_seleccionada.strftime("%Y-%m-%dT%H:%M"),
                "motivo": "clima",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.pedido.refresh_from_db()
        otra_programacion.refresh_from_db()
        self.entrega.refresh_from_db()
        otra_entrega.refresh_from_db()
        self.assertEqual(self.pedido.fecha_entrega_programada, fecha_seleccionada)
        self.assertEqual(self.pedido.estado, Pedido.VEHICULO_ASIGNADO)
        self.assertEqual(self.entrega.conductor_id, self.conductor.pk)
        self.assertEqual(self.entrega.vehiculo_id, self.vehiculo.pk)
        self.assertEqual(otra_programacion.fecha_entrega_programada, otra_fecha)
        self.assertEqual(otra_programacion.estado, Pedido.VEHICULO_ASIGNADO)
        self.assertEqual(otra_entrega.conductor_id, self.conductor.pk)
        self.assertEqual(otra_entrega.vehiculo_id, self.vehiculo_alt.pk)

    def test_reagendar_en_ruta_se_rechaza_y_conserva_programacion(self):
        fecha_original = self.pedido.fecha_entrega_programada
        self.pedido.estado = Pedido.EN_RUTA
        self.pedido.save(update_fields=["estado"])
        self.entrega.estado = "en_ruta"
        self.entrega.save(update_fields=["estado"])
        propuesta = timezone.localtime(timezone.now() + timedelta(days=2)).replace(second=0, microsecond=0)

        response = self.client.post(
            reverse("logistica:reagendar_entrega", args=[self.pedido.codigo_pedido]),
            {
                "fecha_entrega_programada": propuesta.strftime("%Y-%m-%dT%H:%M"),
                "motivo": "clima",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ya está en ruta")
        self.pedido.refresh_from_db()
        self.entrega.refresh_from_db()
        self.assertEqual(self.pedido.fecha_entrega_programada, fecha_original)
        self.assertEqual(self.pedido.estado, Pedido.EN_RUTA)
        self.assertEqual(self.entrega.estado, "en_ruta")
        self.assertEqual(self.entrega.conductor_id, self.conductor.pk)
        self.assertEqual(self.entrega.vehiculo_id, self.vehiculo.pk)

    def test_reagendar_varias_veces_conserva_historial_y_notifica_cada_cambio(self):
        fechas = [
            timezone.localtime(timezone.now() + timedelta(days=d)).replace(second=0, microsecond=0)
            for d in (4, 6)
        ]
        for fecha in fechas:
            response = self.client.post(
                reverse("logistica:reagendar_entrega", args=[self.pedido.codigo_pedido]),
                {
                    "fecha_entrega_programada": fecha.strftime("%Y-%m-%dT%H:%M"),
                    "motivo": "operativo",
                },
            )
            self.assertEqual(response.status_code, 302)

        historial = Historial.objects.filter(
            modulo="pedido",
            elemento_id=str(self.pedido.codigo_pedido),
            descripcion__startswith="Entrega reagendada:",
        )
        notificaciones = Notificacion.objects.filter(
            usuario=self.cliente,
            titulo__startswith="Nueva fecha de entrega",
        )
        self.assertEqual(historial.count(), 2)
        self.assertEqual(notificaciones.count(), 2)
        self.pedido.refresh_from_db()
        self.assertEqual(timezone.localtime(self.pedido.fecha_entrega_programada), fechas[-1])

    def test_conductor_ve_nueva_programacion_y_motivo_del_reagendamiento(self):
        nueva = timezone.localtime(timezone.now() + timedelta(days=5)).replace(second=0, microsecond=0)
        self.client.post(
            reverse("logistica:reagendar_entrega", args=[self.pedido.codigo_pedido]),
            {
                "fecha_entrega_programada": nueva.strftime("%Y-%m-%dT%H:%M"),
                "motivo": "clima",
            },
        )
        self.client.force_login(self.conductor_user)

        response = self.client.get(reverse("usuarios:pedidos_conductor"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, nueva.strftime("%d/%m/%Y %H:%M"))
        self.assertContains(response, "Reagendada")
        self.assertContains(response, "Condiciones climáticas desfavorables")
        self.assertEqual(self.pedido.entregas.count(), 1)

        detalle = self.client.get(
            reverse("usuarios:detalle_entrega_conductor", args=[self.entrega.pk])
        )
        self.assertEqual(detalle.status_code, 200)
        self.assertContains(detalle, "Historial de reagendamientos")
        self.assertContains(detalle, "Condiciones climáticas desfavorables")

        with patch("apps.usuarios.views.get_route_weather", return_value=None):
            panel = self.client.get(reverse("usuarios:panel_conductor"))
        self.assertEqual(panel.status_code, 200)
        self.assertContains(panel, nueva.strftime("%d/%m/%Y %H:%M"))

    def test_no_admite_fecha_pasada(self):
        anterior = timezone.localtime(timezone.now() - timedelta(days=1)).replace(second=0, microsecond=0)
        response = self.client.post(
            reverse("logistica:reagendar_entrega", args=[self.pedido.codigo_pedido]),
            {"fecha_entrega_programada": anterior.strftime("%Y-%m-%dT%H:%M"), "motivo": "clima"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La nueva fecha debe ser futura")

    def test_novedad_de_conductor_propietario_no_cambia_estado(self):
        self.client.force_login(self.conductor_user)
        response = self.client.post(
            reverse("logistica:crear_novedad", args=[self.entrega.pk]),
            {"tipo": "mecanico", "descripcion": "Falla leve durante el recorrido", "solucion": "Se aseguró la carga"},
        )
        self.assertEqual(response.status_code, 302)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.VEHICULO_ASIGNADO)
        self.assertEqual(self.entrega.novedades.get().reportado_por, self.conductor_user)

    def test_admin_registra_novedad_con_evidencia_y_notifica_cliente(self):
        imagen = BytesIO()
        Image.new("RGB", (2, 2), color="orange").save(imagen, format="PNG")
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("logistica:crear_novedad", args=[self.entrega.pk]),
                    {
                        "tipo": "clima",
                        "descripcion": "Lluvia fuerte en la vía de acceso",
                        "solucion": "Se esperó hasta recuperar condiciones seguras",
                        "evidencia": SimpleUploadedFile("lluvia.png", imagen.getvalue(), content_type="image/png"),
                    },
                )
        self.assertEqual(response.status_code, 302)
        novedad = self.entrega.novedades.get()
        self.assertTrue(novedad.evidencia.name.startswith("novedades/"))
        self.assertTrue(Notificacion.objects.filter(usuario=self.cliente, titulo__startswith="Novedad logística").exists())
        self.assertTrue(Historial.objects.filter(modulo="novedad", elemento_id=str(novedad.pk)).exists())
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.VEHICULO_ASIGNADO)

    def test_conductor_no_puede_reportar_novedad_de_otro_envio(self):
        self.client.force_login(self.conductor_alt_user)
        response = self.client.post(
            reverse("logistica:crear_novedad", args=[self.entrega.pk]),
            {"tipo": "demora", "descripcion": "Reporte no autorizado"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.entrega.novedades.exists())

    def test_cliente_puede_consultar_historial_de_cambios(self):
        Historial.objects.create(
            usuario=self.admin,
            accion="editar",
            modulo="pedido",
            elemento_id=str(self.pedido.codigo_pedido),
            descripcion="Entrega reagendada para el 30/11/2026. Motivo: clima.",
        )
        self.client.force_login(self.cliente)
        response = self.client.get(reverse("pedidos:ver_pedido_admin", args=[self.pedido.codigo_pedido]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historial logístico")
        self.assertContains(response, "Entrega reagendada")
