from django.test import TestCase, Client
from django.urls import reverse
from apps.usuarios.models import Usuario
from .models import Entrega, HistorialEstadoEntrega

class TestActualizarEstadoEntrega(TestCase):

    def setUp(self):
        self.client = Client()
        self.conductor = Usuario.objects.create_user(username='conductor1', password='pass')
        self.otro_conductor = Usuario.objects.create_user(username='conductor2', password='pass')
        self.entrega = Entrega.objects.create(conductor=self.conductor, estado='pendiente')
        self.client.force_login(self.conductor)

    def test_transicion_valida_pendiente_a_en_camino(self):
        res = self.client.post(reverse('transporte:actualizar_estado_entrega', args=[self.entrega.id]), {'estado': 'en_camino'})
        self.entrega.refresh_from_db()
        self.assertEqual(self.entrega.estado, 'en_camino')
        self.assertRedirects(res, reverse('transporte:lista_entregas'))

    def test_transicion_invalida_pendiente_a_entregado(self):
        res = self.client.post(reverse('transporte:actualizar_estado_entrega', args=[self.entrega.id]), {'estado': 'entregado'})
        self.entrega.refresh_from_db()
        self.assertEqual(self.entrega.estado, 'pendiente')
        self.assertIn('error', res.context)

    def test_no_modificar_entrega_ya_entregada(self):
        self.entrega.estado = 'entregado'
        self.entrega.save()
        res = self.client.post(reverse('transporte:actualizar_estado_entrega', args=[self.entrega.id]), {'estado': 'en_camino'})
        self.entrega.refresh_from_db()
        self.assertEqual(self.entrega.estado, 'entregado')

    def test_conductor_no_accede_a_entrega_ajena(self):
        entrega_ajena = Entrega.objects.create(conductor=self.otro_conductor, estado='pendiente')
        res = self.client.post(reverse('transporte:actualizar_estado_entrega', args=[entrega_ajena.id]), {'estado': 'en_camino'})
        self.assertEqual(res.status_code, 404)

    def test_historial_se_registra_al_cambiar_estado(self):
        self.client.post(reverse('transporte:actualizar_estado_entrega', args=[self.entrega.id]), {'estado': 'en_camino'})
        historial = HistorialEstadoEntrega.objects.filter(entrega=self.entrega)
        self.assertEqual(historial.count(), 1)
        self.assertEqual(historial.first().estado_anterior, 'pendiente')
        self.assertEqual(historial.first().estado_nuevo, 'en_camino')