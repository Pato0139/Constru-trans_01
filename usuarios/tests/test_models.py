from datetime import date, timedelta
from django.test import TestCase
from usuarios.models import Usuario, Conductor, Vehiculo, ConductorVehiculo, EPS, UnidadMedida, MaterialConstruccion, Stock, MetodoPago


class UsuarioModelTests(TestCase):
    def test_crear_usuario_normal(self):
        """Prueba que se puede crear un usuario correctamente"""
        usuario = Usuario.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            nombres="Test",
            apellidos="User",
            documento="12345678",
            tipo_documento="CC",
            rol="cliente"
        )
        self.assertEqual(usuario.username, "testuser")
        self.assertEqual(usuario.email, "test@example.com")
        self.assertTrue(usuario.check_password("password123"))

    def test_usuario_tiene_iniciales(self):
        """Prueba la propiedad iniciales"""
        usuario = Usuario.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            nombres="Juan Carlos",
            apellidos="Perez",
            documento="12345678",
            tipo_documento="CC",
            rol="cliente"
        )
        self.assertEqual(usuario.iniciales, "JC")


class ConductorModelTests(TestCase):
    def test_crear_conductor(self):
        """Prueba crear un conductor con su perfil"""
        eps = EPS.objects.create(
            codigo_eps="EPS001",
            numero_seguro="123456",
            ciudad="Tunja",
            direccion="Calle 1",
            telefono="123456",
            correo="eps@test.com"
        )
        usuario = Usuario.objects.create_user(
            username="conductor1",
            email="conductor@test.com",
            password="password123",
            nombres="Conductor",
            apellidos="Test",
            documento="987654",
            tipo_documento="CC",
            rol="conductor"
        )
        conductor = Conductor.objects.create(
            usuario=usuario,
            numero_licencia="LIC123",
            categoria_licencia="C2",
            fecha_vencimiento_licencia=date.today() + timedelta(days=365),
            estado="activo",
            eps=eps
        )
        self.assertEqual(conductor.usuario, usuario)
        self.assertEqual(conductor.numero_licencia, "LIC123")


class VehiculoModelTests(TestCase):
    def test_crear_vehiculo(self):
        """Prueba crear un vehículo"""
        vehiculo = Vehiculo.objects.create(
            placa="ABC123",
            marca="Toyota",
            modelo="Hiace",
            tipo_vehiculo="Bolqueta",
            capacidad_carga=10.00,
            estado="disponible"
        )
        self.assertEqual(vehiculo.placa, "ABC123")
        self.assertEqual(vehiculo.id, vehiculo.id_vehiculo)


class ConductorVehiculoModelTests(TestCase):
    def test_asignar_vehiculo(self):
        """Prueba la asignación de vehículo a conductor"""
        usuario = Usuario.objects.create_user(
            username="conductor2",
            email="conductor2@test.com",
            password="password123",
            nombres="Conductor",
            apellidos="Dos",
            documento="111222333",
            tipo_documento="CC",
            rol="conductor"
        )
        conductor = Conductor.objects.create(
            usuario=usuario,
            numero_licencia="LIC456",
            categoria_licencia="C2",
            fecha_vencimiento_licencia=date.today() + timedelta(days=365),
            estado="activo"
        )
        vehiculo = Vehiculo.objects.create(
            placa="DEF456",
            marca="Nissan",
            modelo="D21",
            tipo_vehiculo="Camion",
            capacidad_carga=8.00,
            estado="disponible"
        )
        asignacion = ConductorVehiculo.objects.create(
            conductor=conductor,
            vehiculo=vehiculo
        )
        self.assertEqual(asignacion.conductor, conductor)
        self.assertEqual(asignacion.vehiculo, vehiculo)
        self.assertIsNone(asignacion.fecha_fin)
