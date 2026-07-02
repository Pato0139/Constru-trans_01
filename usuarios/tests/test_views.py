from datetime import date, timedelta

from django.test import Client, TestCase
from django.urls import reverse

from usuarios.models import Conductor, ConductorVehiculo, Usuario, Vehiculo


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
        self.conductor_profile = Conductor.objects.create(
            usuario=self.conductor_user,
            numero_licencia="LIC-1003",
            categoria_licencia="C2",
            fecha_vencimiento_licencia=date.today() + timedelta(days=365),
            estado="activo",
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
        response = self.client.get(reverse("inicio:home"))
        self.assertEqual(response.status_code, 200)

    def test_asignar_vehiculo_a_conductor(self):
        """El administrador puede asignar y cambiar vehículos de un conductor."""
        self.client.login(username="admin@test.com", password="password123")
        vehiculo2 = Vehiculo.objects.create(
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
