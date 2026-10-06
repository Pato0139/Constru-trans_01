import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.ia.models import KnowledgeBase
from apps.ia.services import context_service, kb_service

User = get_user_model()


class IAViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            nombres="Admin",
            apellidos="Test",
            rol="admin",
            estado="activo",
        )
        self.cliente_user = User.objects.create_user(
            email="cliente@test.com",
            password="testpass123",
            nombres="Cliente",
            apellidos="Test",
            rol="cliente",
            estado="activo",
        )
        self.conductor_user = User.objects.create_user(
            email="conductor@test.com",
            password="testpass123",
            nombres="Conductor",
            apellidos="Test",
            rol="conductor",
            estado="activo",
        )

    def test_chat_ia_requiere_login(self):
        response = self.client.post(
            reverse("chat_ia"), json.dumps({"mensaje": "hola"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 302)  # Redirige a login

    def test_feedback_ia_requiere_login(self):
        response = self.client.post(
            reverse("feedback_ia"),
            json.dumps({"feedback": "good"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_chat_ia_con_login_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("chat_ia"),
            json.dumps({"mensaje": "¿Cuántos usuarios hay?"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("respuesta", response.json())


class KBServiceTests(TestCase):
    def test_escapar_regex(self):
        pregunta = "¿Cuántos materiales hay?"
        kb_service.update_knowledge_base(pregunta, "Hay 100 materiales", "good")
        entry = KnowledgeBase.objects.filter(best_response="Hay 100 materiales").first()
        self.assertIsNotNone(entry)
        self.assertIn("\\?", entry.question_pattern)  # El ? debe estar escapado

    def test_check_knowledge_base_con_pattern_escapado(self):
        pregunta_escapada = "\\¿Cuántos usuarios hay\\?"
        KnowledgeBase.objects.create(
            question_pattern=pregunta_escapada, best_response="Hay 50 usuarios", category="general"
        )
        resultado = kb_service.check_knowledge_base("¿Cuántos usuarios hay?")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.best_response, "Hay 50 usuarios")


class ContextServiceTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            nombres="Admin",
            apellidos="Test",
            rol="admin",
            estado="activo",
        )
        self.cliente_user = User.objects.create_user(
            email="cliente@test.com",
            password="testpass123",
            nombres="Cliente",
            apellidos="Test",
            rol="cliente",
            estado="activo",
        )
        self.conductor_user = User.objects.create_user(
            email="conductor@test.com",
            password="testpass123",
            nombres="Conductor",
            apellidos="Test",
            rol="conductor",
            estado="activo",
        )

    def test_datos_globales_solo_para_admin(self):
        datos_admin = context_service.obtener_contexto_datos(usuario=self.admin_user)
        self.assertIn("total_usuarios", datos_admin)

        datos_cliente = context_service.obtener_contexto_datos(usuario=self.cliente_user)
        self.assertNotIn("total_usuarios", datos_cliente)
        self.assertIn("mis_pedidos_totales", datos_cliente)

        datos_conductor = context_service.obtener_contexto_datos(usuario=self.conductor_user)
        self.assertNotIn("total_usuarios", datos_conductor)
        self.assertIn("mis_entregas_pendientes", datos_conductor)
