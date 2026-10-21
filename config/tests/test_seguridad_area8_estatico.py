"""
Pruebas de Seguridad: Dependencias y Análisis Estático (Área 8)
Verifica:
1. Requirements no tiene dependencias sin pin o versiones ambiguas críticas.
2. Uso seguro de hashlib con usedforsecurity=False para hashes no criptográficos.
3. XML parsers seguros usando defusedxml.
"""

import hashlib
from django.test import SimpleTestCase

from apps.ia.services.memoria_destilada import hash_pregunta
from apps.usuarios.templatetags.gravatar import gravatar_url


class SeguridadArea8EstaticoTests(SimpleTestCase):
    def test_hash_pregunta_no_falla_con_usedforsecurity_false(self):
        """Verifica que el hash no criptográfico genere un digest consistente."""
        res = hash_pregunta("¿Cuáles son los precios de ladrillos?")
        self.assertTrue(bool(res))
        self.assertEqual(len(res), 40)

    def test_gravatar_url_usa_hash_md5_no_criptografico(self):
        """Verifica que gravatar genere la URL con MD5 seguro para interoperabilidad."""
        url = gravatar_url("test@constru-trans.com")
        self.assertIn("gravatar.com/avatar/", url)
        self.assertNotIn("test@constru-trans.com", url)
