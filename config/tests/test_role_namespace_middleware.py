from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase

from config.middleware import RoleNamespaceMiddleware


class RoleNamespaceMiddlewareTests(SimpleTestCase):
    def test_conductor_can_reach_order_detail_route(self):
        request = RequestFactory().get("/pedidos/detalle/170/")
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            email="driver@example.invalid",
            username="driver",
            rol="conductor",
        )
        response_marker = object()
        middleware = RoleNamespaceMiddleware(lambda _request: response_marker)

        self.assertIs(middleware(request), response_marker)
