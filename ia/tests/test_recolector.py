import json
from pathlib import Path
from django.test import TestCase

KB_PATH = Path("ia/training/ia_knowledge_base.json")


class CorpusCuradoTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.kb = json.loads(KB_PATH.read_text(encoding="utf-8-sig"))

    def test_tiene_faqs_suficientes(self):
        self.assertGreaterEqual(len(self.kb["faq_entries"]), 30)

    def test_ids_unicos(self):
        ids = [faq["id"] for faq in self.kb["faq_entries"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_schema_faqs(self):
        for faq in self.kb["faq_entries"]:
            self.assertTrue(faq["question_patterns"])
            self.assertTrue(faq["best_response"].strip())

    def test_faqs_dominio_presentes(self):
        ids = {faq["id"] for faq in self.kb["faq_entries"]}
        for esperado in ["faq_020", "faq_021", "faq_030", "faq_032", "faq_041"]:
            self.assertIn(esperado, ids)


class RecolectorTests(TestCase):
    def test_categorias_semilla_definidas(self):
        from ia.training.recolector_preguntas import CATEGORIAS_DOMINIO
        self.assertGreaterEqual(len(CATEGORIAS_DOMINIO), 8)
        self.assertTrue(all(c.startswith("Categoría:") for c in CATEGORIAS_DOMINIO))

    def test_fuente_desconocida(self):
        from ia.training.recolector_preguntas import recolectar
        self.assertEqual(recolectar(0, fuentes=["inexistente"]), [])

    def test_estructura_del_par(self):
        from ia.training.recolector_preguntas import recolectar_opentdb
        with __import__("unittest").mock.patch("ia.training.recolector_preguntas.requests.get") as get:
            get.return_value.json.return_value = {"results": [{"question": "Q?", "category": "C", "correct_answer": "A", "difficulty": "easy"}]}
            get.return_value.raise_for_status.return_value = None
            pregunta = recolectar_opentdb(1)[0]
        self.assertIn("pregunta", pregunta)
        self.assertIn("fuente", pregunta)
        self.assertIn("metadata", pregunta)
        self.assertIn("licencia", pregunta["metadata"])
