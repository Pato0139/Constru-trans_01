from unittest.mock import MagicMock, patch
from django.test import TestCase
from ia.services import assistant_service, llm_service
from ia.services.web_search_service import _es_pregunta_general


class RouterGeneralTests(TestCase):
    def test_pregunta_general_detectada(self):
        self.assertTrue(_es_pregunta_general("¿Quién fue Simón Bolívar?"))
        self.assertTrue(_es_pregunta_general("¿Qué es la fotosíntesis?"))
        self.assertTrue(_es_pregunta_general("¿Cómo se hace un bizcocho?"))

    def test_pregunta_del_sistema_no_es_general(self):
        self.assertFalse(_es_pregunta_general("¿Cuál es el estado del pedido 154?"))
        self.assertFalse(_es_pregunta_general("¿Cuántos materiales hay en el inventario?"))


class PromptGeneralTests(TestCase):
    def test_prompt_incluye_bloques_rag_y_web(self):
        prompt = llm_service.construir_prompt_sistema({"total_usuarios": 12}, "Andrés", contexto_rag="Material: Cemento 50kg", contexto_web="- Resultado de búsqueda actual")
        self.assertIn("Constru-Trans", prompt)
        self.assertIn("Documentos relevantes", prompt)
        self.assertIn("Información web actualizada", prompt)
        self.assertIn("Preguntas generales", prompt)

    def test_prompt_sin_rag_ni_web_no_incluye_bloques(self):
        prompt = llm_service.construir_prompt_sistema({}, "Invitado")
        self.assertNotIn("Información interna relevante", prompt)
        self.assertNotIn("Información web actualizada", prompt)


class PreguntarIAFlowTests(TestCase):
    def test_pregunta_general_llega_al_llm(self):
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="Simón Bolívar fue un libertador."))])
        with patch.object(llm_service, "client", fake_client), patch.object(assistant_service, "get_conversation", return_value=MagicMock(id=1)), patch.object(assistant_service, "add_message_to_conversation", return_value=MagicMock(id=99)), patch.object(assistant_service, "guardar_interaccion"):
            respuesta, message_id = assistant_service.preguntar_ia("¿Quién fue Simón Bolívar?", usuario=None, historial=[], session_id="test-s1")
        self.assertIn("Simón Bolívar", respuesta)
        self.assertEqual(message_id, 99)

    def test_pregunta_del_sistema_funciona_sin_llm(self):
        with patch.object(llm_service, "client", None), patch.object(assistant_service, "get_conversation", return_value=MagicMock(id=2)), patch.object(assistant_service, "add_message_to_conversation", return_value=MagicMock(id=100)):
            respuesta, _ = assistant_service.preguntar_ia("¿Qué es Constru-Trans?", usuario=None, historial=[], session_id="test-s2")
        self.assertIn("Constru-Trans", respuesta)
