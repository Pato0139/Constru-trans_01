import json
from unittest.mock import MagicMock, patch
from django.test import TestCase
from ia.services import llm_service, tools_registry


class ToolsRegistryTests(TestCase):
    def test_definiciones_validas(self):
        tools = tools_registry._tools_definiciones()
        self.assertGreaterEqual(len(tools), 5)
        nombres = {tool["function"]["name"] for tool in tools}
        self.assertIn("consultar_estado_pedido", nombres)
        self.assertIn("calcular", nombres)

    def test_dispatch_calcular(self):
        resultado = json.loads(tools_registry.ejecutar_tool("calcular", '{"expresion": "12*8+4"}'))
        self.assertIn("resultado", resultado)

    def test_dispatch_desconocida(self):
        self.assertIn("error", json.loads(tools_registry.ejecutar_tool("no_existe", "{}")))

    def test_dispatch_argumentos_invalidos(self):
        self.assertIn("error", json.loads(tools_registry.ejecutar_tool("calcular", "no-soy-json")))


class ToolCallingLoopTests(TestCase):
    def _respuesta(self, contenido, tool_calls=None):
        return MagicMock(choices=[MagicMock(message=MagicMock(content=contenido, tool_calls=tool_calls))])

    def test_sin_tools(self):
        fake = MagicMock()
        fake.chat.completions.create.return_value = self._respuesta("Respuesta directa")
        with patch.object(llm_service, "client", fake), patch.object(tools_registry, "TOOLS_ENABLED", False):
            self.assertEqual(llm_service.preguntar_llm("hola", {}, "Test", []), "Respuesta directa")

    def test_tool_call_roundtrip(self):
        tool_call = MagicMock(id="call_1", function=MagicMock(name="calcular", arguments='{"expresion": "2500*12"}'))
        fake = MagicMock()
        fake.chat.completions.create.side_effect = [self._respuesta(None, [tool_call]), self._respuesta("Son 30.000")]
        with patch.object(llm_service, "client", fake), patch.object(tools_registry, "TOOLS_ENABLED", True):
            resultado = llm_service.preguntar_llm("¿Cuánto es 2500*12?", {}, "Test", [])
        self.assertEqual(resultado, "Son 30.000")
        mensajes = fake.chat.completions.create.call_args_list[1].kwargs["messages"]
        self.assertTrue(any(isinstance(mensaje, dict) and mensaje.get("role") == "tool" for mensaje in mensajes))
