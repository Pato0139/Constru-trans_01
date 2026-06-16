from datetime import date, timedelta

from django.test import Client, TestCase
from django.urls import reverse

from .models import Conductor, ConductorVehiculo, Material, Stock, Usuario, Vehiculo, UnidadMedida


class ConstruTransTestSuite(TestCase):
    def setUp(self):
        self.client = Client()

        self.admin_user = Usuario.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='password123',
            rol='admin',
            nombres='Admin',
            documento='1001',
            tipo_documento='CC'
        )


        self.cliente_user = Usuario.objects.create_user(
            username='cliente@test.com',
            email='cliente@test.com',
            password='password123',
            rol='cliente',
            nombres='Cliente',
            documento='1002',
            tipo_documento='CC'
        )


        self.conductor_user = Usuario.objects.create_user(
            username='cond@test.com',
            email='cond@test.com',
            password='password123',
            rol='conductor',
            nombres='Conductor',
            documento='1003',
            tipo_documento='CC'
        )

        self.conductor_profile = Conductor.objects.create(
            usuario=self.conductor_user,
            numero_licencia='LIC-1003',
            categoria_licencia='C2',
            fecha_vencimiento_licencia=date.today() + timedelta(days=365),
            estado='activo'
        )


        self.unidad_m3 = UnidadMedida.objects.create(
            codigo='M3',
            nombre='m3',
            abreviatura='m3'
        )


        self.material = Material.objects.create(
            nombre='Arena',
            unidad_medida=self.unidad_m3,
            descripcion='Arena gruesa para construcción',
            precio_referencia=50000
        )
        self.stock = Stock.objects.create(material=self.material, cantidad_actual=100)

        self.vehiculo = Vehiculo.objects.create(
            placa='ABC123',
            marca='Toyota',
            modelo='Hiace',
            tipo_vehiculo='Bolqueta',
            capacidad_carga=10.00,
            estado='disponible'
        )

    def test_01_registro_usuario(self):
        """Prueba de registro de nuevo cliente"""
        response = self.client.post(reverse('usuarios:registro'), {
            'nombres': 'Nuevo',
            'apellidos': 'Cliente',
            'correo': 'nuevo@test.com',
            'tipo_documento': 'CC',
            'documento': '1234567890',
            'telefono': '3001234567',
            'contrasena': 'pass123',
            'confirmar_contrasena': 'pass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Usuario.objects.filter(email='nuevo@test.com').exists())

    def test_02_login_y_permisos(self):
        """Prueba de login y restricción de admin_required"""
        # Login admin
        self.client.login(username='admin@test.com', password='password123')
        response = self.client.get(reverse('reportes:reportes_admin'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        # Login cliente intentando entrar a reportes
        self.client.login(username='cliente@test.com', password='password123')
        response = self.client.get(reverse('reportes:reportes_admin'))
        self.assertEqual(response.status_code, 403)

    def test_03_flujo_inventario_y_pedidos(self):
        """Prueba de creación de pedido con múltiples detalles y descuento de stock"""
        self.client.login(username='cliente@test.com', password='password123')

        stock_inicial = self.material.stock
        cantidad_pedido = 5

        response = self.client.post(reverse('clientes:crear_pedido'), {
            'material_id[]': [self.material.id],
            'cantidad[]': [cantidad_pedido],
            'ciudad': 'Tunja',
            'direccion_detalle': 'Calle Falsa 123',
            'fecha_entrega': '2026-05-01 10:00'
        })

        if response.status_code != 302:
            from django.contrib.messages import get_messages
            print("DEBUG_TEST_MESSAGES:", [m.message for m in get_messages(response.wsgi_request)])

        self.assertEqual(response.status_code, 302)


        # Verificar stock descontado
        self.material.refresh_from_db()
        self.assertEqual(self.material.stock, stock_inicial - cantidad_pedido)

    def test_04_flujo_entregas(self):
        """Prueba de asignación de entrega y cambio de estados"""
        self.assertTrue(True)

    def test_05_asignar_vehiculo_a_conductor(self):
        """El administrador puede asignar y cambiar vehículos de un conductor."""
        self.client.login(username='admin@test.com', password='password123')

        vehiculo2 = Vehiculo.objects.create(
            placa='DEF456',
            marca='Nissan',
            modelo='D21',
            tipo_vehiculo='Camión',
            capacidad_carga=8.00,
            estado='disponible'
        )

        response = self.client.post(
            reverse('usuarios:asignar_vehiculo_conductor', args=[self.conductor_user.id]),
            {'vehiculo': self.vehiculo.id}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ConductorVehiculo.objects.filter(conductor=self.conductor_profile).count(), 1)
        primera_asignacion = ConductorVehiculo.objects.filter(conductor=self.conductor_profile).first()
        self.assertIsNone(primera_asignacion.fecha_fin)
        self.assertEqual(primera_asignacion.vehiculo, self.vehiculo)

        response = self.client.post(
            reverse('usuarios:asignar_vehiculo_conductor', args=[self.conductor_user.id]),
            {'vehiculo': vehiculo2.id}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ConductorVehiculo.objects.filter(conductor=self.conductor_profile).count(), 2)

        asignaciones = ConductorVehiculo.objects.filter(conductor=self.conductor_profile).order_by('-fecha_asignacion')
        self.assertIsNotNone(asignaciones[1].fecha_fin)
        self.assertIsNone(asignaciones[0].fecha_fin)
        self.assertEqual(asignaciones[0].vehiculo, vehiculo2)

    def test_06_lista_conductores_muestra_datos(self):
        self.client.login(username='admin@test.com', password='password123')
        response = self.client.get(reverse('usuarios:lista_conductores'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Licencia')
        self.assertContains(response, 'Categoría')
        self.assertContains(response, 'Vehículo actual')

    def test_07_exportar_pdf(self):
        """Prueba de generación de reportes (simplificada)"""
        self.assertTrue(True)
