
import os
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.contrib.auth.models import User
from apps.usuarios.models import Usuario
from apps.clientes.models import Cliente
from apps.ordenes.models import Pedido

print("Testing Pedido creation...")

# First, check if we have a user
try:
    u = User.objects.get(username='constructora_alfa')
    print(f"Found User: {u}")
    usuario = Usuario.objects.get(user=u)
    print(f"Found Usuario: {usuario}")
    cliente = Cliente.objects.get(usuario=usuario)
    print(f"Found Cliente: {cliente}")
    
    print("\nTrying to create Pedido...")
    # Try creating without cliente first
    pedido = Pedido.objects.create(
        usuario=usuario,
        direccion_destino="Test",
        estado="pendiente"
    )
    print(f"SUCCESS! Pedido created: {pedido}")
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
