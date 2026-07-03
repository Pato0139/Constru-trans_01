import os
import sys

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django

django.setup()

from django.contrib.auth.models import User

from clientes.models import Cliente
from ordenes.models import Pedido
from usuarios.models import EPS, Usuario

print("=== DEBUG: Creating data step by step ===")

try:
    # 1. Create EPS first
    print("\n1. Creating EPS...")
    eps, _ = EPS.objects.get_or_create(
        codigo_eps="EPS001",
        defaults={
            "numero_seguro": "123456789",
            "ciudad": "Bogota",
            "direccion": "Calle 100 # 10-10",
            "telefono": "3101234567",
            "correo": "contacto@eps.com",
        },
    )
    print(f"   [OK] EPS created: {eps}")

    # 2. Create a test user and client
    print("\n2. Creating test client...")
    u_cl, _ = User.objects.get_or_create(
        username="test_client", defaults={"email": "test@test.com"}
    )
    u_cl.set_password("test12345")
    u_cl.save()

    p_cl, _ = Usuario.objects.get_or_create(
        user=u_cl,
        defaults={
            "rol": "cliente",
            "nombres": "Test",
            "apellidos": "Client",
            "documento": "123456",
            "tipo_documento": "CC",
            "estado": "activo",
        },
    )
    print(f"   [OK] Usuario created: {p_cl}")

    cliente_perfil, _ = Cliente.objects.get_or_create(
        usuario=p_cl,
        defaults={
            "nombre_empresa": "Test Company",
            "direccion_principal": "Test Street",
            "tipo_cliente": "empresa",
        },
    )
    print(f"   [OK] Cliente created: {cliente_perfil}")

    # 3. Try creating Pedido in multiple ways
    print("\n3. Testing Pedido creation...")

    print("\n   a. Try with only usuario:")
    try:
        pedido1 = Pedido.objects.create(
            usuario=p_cl, direccion_destino="Test 1", estado="pendiente"
        )
        print(f"      [OK] SUCCESS! Pedido created: {pedido1}")
    except Exception as e:
        print(f"      [ERROR] FAILED: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

    print("\n   b. Try with usuario and cliente:")
    try:
        pedido2 = Pedido.objects.create(
            usuario=p_cl, cliente=cliente_perfil, direccion_destino="Test 2", estado="pendiente"
        )
        print(f"      [OK] SUCCESS! Pedido created: {pedido2}")
    except Exception as e:
        print(f"      [ERROR] FAILED: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

except Exception as e:
    print(f"\n[ERROR] FATAL ERROR: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
