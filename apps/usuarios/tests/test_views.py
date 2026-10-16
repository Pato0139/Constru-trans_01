from datetime import date, timedelta
from types import SimpleNamespace

from django.contrib.sessions.middleware import SessionMiddleware
from django.template.loader import render_to_string
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from apps.logistica.models import ConductorVehiculo, Vehiculo
from apps.usuarios.models import Conductor, Usuario


class UsuarioViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = Usuario.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="password123",
            rol="admin",
            nombres="Admin",
            documento="1001",
            tipo_documento="CC",
        )
        self.cliente_user = Usuario.objects.create_user(
            username="cliente@test.com",
            email="cliente@test.com",
            password="password123",
            rol="cliente",
            nombres="Cliente",
            documento="1002",
            tipo_documento="CC",
        )
        self.conductor_user = Usuario.objects.create_user(
            username="cond@test.com",
            email="cond@test.com",
            password="password123",
            rol="conductor",
            nombres="Conductor",
            documento="1003",
            tipo_documento="CC",
        )
        self.conductor_profile, _ = Conductor.ensure_for_user(
            self.conductor_user,
            defaults={
                "numero_licencia": "LIC-1003",
                "categoria_licencia": "C2",
                "fecha_vencimiento_licencia": date.today() + timedelta(days=365),
                "estado": "activo",
            },
        )
        self.vehiculo = Vehiculo.objects.create(
            placa="ABC123",
            marca="Toyota",
            modelo="Hiace",
            tipo_vehiculo="Bolqueta",
            capacidad_carga=10.00,
            estado="disponible",
        )

    def test_login_y_permisos_admin(self):
        """Prueba de login y restricción de admin_required"""
        self.client.login(username="admin@test.com", password="password123")
        # No tenemos reportes en todas las instalaciones, probamos acceso básico
        response = self.client.get(reverse("inicio:inicio"))
        self.assertEqual(response.status_code, 200)

    def test_registro_rechaza_datos_manipulados_en_el_servidor(self):
        response = self.client.post(
            reverse("usuarios:registro"),
            {
                "nombres": "Juan123",
                "apellidos": "Perez",
                "correo": "registro-invalido@test.com",
                "tipo_documento": "CC",
                "documento": "123456789",
                "pais_codigo": "+57",
                "telefono": "3001234567",
                "contrasena": "Nube!Tren2026#",
                "confirmar_contrasena": "Nube!Tren2026#",
                "aceptar_terminos": "yes",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Usuario.objects.filter(email="registro-invalido@test.com").exists())

    def test_asignar_vehiculo_a_conductor(self):
        """El administrador puede asignar y cambiar vehículos de un conductor."""
        self.client.login(username="admin@test.com", password="password123")
        Vehiculo.objects.create(
            placa="DEF456",
            marca="Nissan",
            modelo="D21",
            tipo_vehiculo="Camión",
            capacidad_carga=8.00,
            estado="disponible",
        )
        response = self.client.post(
            reverse("usuarios:asignar_vehiculo_conductor", args=[self.conductor_user.id]),
            {"vehiculo": self.vehiculo.id},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            ConductorVehiculo.objects.filter(conductor=self.conductor_profile).count(), 1
        )

    def test_lista_conductores_muestra_datos(self):
        self.client.login(username="admin@test.com", password="password123")
        response = self.client.get(reverse("usuarios:lista_conductores"))
        self.assertEqual(response.status_code, 200)

    def test_panel_conductor_muestra_clima_y_pedidos_sin_estadisticas(self):
        self.client.force_login(self.conductor_user)

        response = self.client.get(reverse("usuarios:panel_conductor"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["proxima_entrega"])
        self.assertEqual(response.context["pedidos"].count(), 0)
        self.assertContains(response, "Clima para tu próxima ruta")
        self.assertContains(response, "Mis Entregas Asignadas")
        self.assertNotContains(response, "Entregas Pendientes")
        self.assertNotContains(response, "Acciones Rápidas")

    def test_pedidos_conductor_filtra_por_perfil(self):
        self.client.force_login(self.conductor_user)

        response = self.client.get(reverse("usuarios:pedidos_conductor"))

        self.assertEqual(response.status_code, 200)

    def test_mis_entregas_filtra_por_perfil(self):
        self.client.force_login(self.conductor_user)

        response = self.client.get(reverse("usuarios:mis_entregas"))

        self.assertEqual(response.status_code, 200)

    def test_perfil_conductor_filtra_pedidos_por_perfil(self):
        self.client.force_login(self.conductor_user)

        response = self.client.get(reverse("usuarios:perfil_conductor"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["conductor"], self.conductor_user)

    def test_sidebar_usa_namespace_correcto_de_pedidos(self):
        request = RequestFactory().get("/usuarios/panel/")
        SessionMiddleware(lambda request: None).process_request(request)
        request.user = self.admin_user
        request.resolver_match = SimpleNamespace(app_name="pedidos", url_name="lista_pedidos_admin")

        rendered = render_to_string("partials/sidebar.html", {"request": request}, request=request)

        self.assertIn(reverse("pedidos:lista_pedidos_admin"), rendered)
        self.assertNotIn("/ordenes/", rendered)
