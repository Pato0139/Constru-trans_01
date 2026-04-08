from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Material

User = get_user_model()


class MaterialModelTest(TestCase):
    def setUp(self):
        self.material = Material.objects.create(
            nombre='Cemento Portland',
            tipo='Cemento',
            precio=25000.00,
            stock=100
        )

    def test_material_creado_correctamente(self):
        self.assertEqual(self.material.nombre, 'Cemento Portland')
        self.assertEqual(self.material.stock, 100)

    def test_str_representation(self):
        self.assertIn('Cemento Portland', str(self.material))

    def test_material_activo_por_defecto(self):
        self.assertTrue(self.material.activo)


class MaterialesVistaTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test', password='test1234')
        self.client.login(username='test', password='test1234')
        Material.objects.create(nombre='Varilla', tipo='Herramientas', precio=15000, stock=50)
        Material.objects.create(nombre='Tabla pino', tipo='Arena', precio=8000, stock=3)
        Material.objects.create(nombre='Pintura', tipo='Cemento', precio=35000, stock=0)

    def test_vista_requiere_login(self):
        self.client.logout()
        response = self.client.get(reverse('inventario:materiales_lista'))
        self.assertNotEqual(response.status_code, 200)

    def test_vista_carga_correctamente(self):
        response = self.client.get(reverse('inventario:materiales_lista'))
        self.assertEqual(response.status_code, 200)

    def test_busqueda_por_nombre(self):
        response = self.client.get(reverse('inventario:materiales_lista'), {'q': 'Varilla'})
        self.assertContains(response, 'Varilla')
        self.assertNotContains(response, 'Tabla pino')

    def test_filtro_por_tipo(self):
        response = self.client.get(reverse('inventario:materiales_lista'), {'tipo': 'Arena'})
        self.assertContains(response, 'Tabla pino')
        self.assertNotContains(response, 'Varilla')

    def test_filtro_stock_minimo(self):
        response = self.client.get(reverse('inventario:materiales_lista'), {'stock_min': '10'})
        self.assertContains(response, 'Varilla')
        self.assertNotContains(response, 'Pintura')

    def test_paginacion(self):
        for i in range(15):
            Material.objects.create(nombre=f'Mat{i}', tipo='Otro', precio=1000, stock=10)
        response = self.client.get(reverse('inventario:materiales_lista'), {'page': 1})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['page_obj'].has_next())