from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Usuario, Material, Stock, Proveedor, Vehiculo
from apps.ordenes.models import Orden, DetalleOrden, Entrega
from django.urls import reverse
import decimal

class ConstruTransTestSuite(TestCase):
    def setUp(self):
        self.client = Client()
        # 1. Crear Admin
        self.admin_user = User.objects.create_user(username='admin@test.com', email='admin@test.com', password='password123')
        self.admin_perfil = Usuario.objects.create(user=self.admin_user, rol='admin', nombres='Admin', documento='1001')
        
        # 2. Crear Cliente
        self.cliente_user = User.objects.create_user(username='cliente@test.com', email='cliente@test.com', password='password123')
        self.cliente_perfil = Usuario.objects.create(user=self.cliente_user, rol='cliente', nombres='Cliente', documento='1002')
        
        # 3. Crear Conductor
        self.conductor_user = User.objects.create_user(username='cond@test.com', email='cond@test.com', password='password123')
        self.conductor_perfil = Usuario.objects.create(user=self.conductor_user, rol='conductor', nombres='Conductor', documento='1003')

        # 4. Crear Material y su Stock (via signals)
        self.material = Material.objects.create(nombre='Arena', tipo='Agregados', precio=50000)
        self.stock = self.material.stock_info
        self.stock.cantidad = 100
        self.stock.save()

        # 5. Vehículo (asignado al conductor)
        self.vehiculo = Vehiculo.objects.create(
            placa='ABC123', 
            tipo='Bolqueta', 
            capacidad='10m3', 
            estado='disponible',
            conductor=self.conductor_perfil
        )

    def test_01_registro_usuario(self):
        """Prueba de registro de nuevo cliente"""
        response = self.client.post(reverse('usuarios:registro'), {
            'nombres': 'Nuevo',
            'apellidos': 'Cliente',
            'correo': 'nuevo@test.com',
            'tipo_documento': 'CC',
            'documento': '9999',
            'telefono': '300',
            'contrasena': 'pass123',
            'confirmar_contrasena': 'pass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email='nuevo@test.com').exists())

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
        self.assertEqual(response.status_code, 403) # PermissionDenied

    def test_03_flujo_inventario_y_pedidos(self):
        """Prueba de creación de pedido con múltiples detalles y descuento de stock"""
        self.client.login(username='cliente@test.com', password='password123')
        
        stock_inicial = self.material.stock
        cantidad_pedido = 5
        
        response = self.client.post(reverse('clientes:crear_pedido'), {
            'material_id[]': [self.material.id],
            'cantidad[]': [cantidad_pedido],
            'direccion': 'Calle Falsa 123',
            'fecha_entrega': '2026-05-01 10:00'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verificar stock descontado
        self.material.refresh_from_db()
        self.assertEqual(self.material.stock, stock_inicial - cantidad_pedido)
        
        # Verificar orden y detalles
        orden = Orden.objects.latest('id')
        self.assertEqual(orden.detalles.count(), 1)
        self.assertEqual(orden.precio, self.material.precio * cantidad_pedido)

    def test_04_flujo_entregas(self):
        """Prueba de asignación de entrega y cambio de estados"""
        # Crear una orden previa
        orden = Orden.objects.create(cliente=self.cliente_perfil, direccion_destino='Test')
        DetalleOrden.objects.create(orden=orden, material=self.material, cantidad=1, precio_unitario=self.material.precio)
        
        self.client.login(username='admin@test.com', password='password123')
        
        # Asignar entrega (pasa a en_ruta)
        response = self.client.post(reverse('ordenes:crear_entrega', args=[orden.id]), {
            'conductor': self.conductor_perfil.id,
            'vehiculo': self.vehiculo.id
        })
        
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'en_ruta')
        
        # Finalizar entrega
        entrega = orden.entregas.first()
        entrega.estado = 'entregado'
        entrega.save() # Signal actualizar_estado_orden actúa aquí
        
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'entregado')
        self.assertIsNotNone(orden.fecha_entrega_real)

    def test_05_exportar_pdf(self):
        """Prueba de generación de factura y reportes PDF"""
        orden = Orden.objects.create(cliente=self.cliente_perfil, direccion_destino='Test', precio=1000)
        self.client.login(username='admin@test.com', password='password123')
        
        # Factura
        response = self.client.get(reverse('ordenes:descargar_factura', args=[orden.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
        # Reporte
        response = self.client.get(reverse('reportes:exportar_reporte_pdf', args=['materiales']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
