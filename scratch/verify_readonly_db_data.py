import os
import sys
import django

sys.path.insert(0, ".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.usuarios.models import Usuario
from apps.pagos.models import Factura, Pago, DetallePago, PagoFactura
from apps.logistica.models import Vehiculo, Entrega
from apps.pedidos.models import Pedido
import re

print("=== VERIFICACIÓN DE SOLO LECTURA EN BASE DE DATOS ===")

# 1. Administradores e is_staff
admins = Usuario.objects.filter(rol="admin")
print(f"Total usuarios con rol='admin': {admins.count()}")
for a in admins:
    print(f"  - Admin: pk={a.pk}, username={a.username}, email={a.email}, is_staff={a.is_staff}, is_superuser={a.is_superuser}, is_active={a.is_active}")
    if not a.is_staff:
        print(f"    [ALERTA] Admin pk={a.pk} NO TIENE is_staff=True!")

# 2. Factura counts & PK analysis
facturas_count = Factura.objects.count()
print(f"\nTotal Facturas: {facturas_count}")
facturas_invalidas = Factura.objects.filter(total__lt=0) | Factura.objects.filter(subtotal__lt=0) | Factura.objects.filter(impuestos__lt=0)
print(f"Facturas con montos < 0: {facturas_invalidas.count()}")

discrepancias_total = 0
for f in Factura.objects.all():
    if f.total != (f.subtotal + f.impuestos):
        discrepancias_total += 1
print(f"Facturas con total != subtotal + impuestos: {discrepancias_total}")

# FKs pointing to Factura
pagos_factura_count = PagoFactura.objects.count()
print(f"Total PagoFactura (FK a Factura): {pagos_factura_count}")

# 3. Vehiculos
vehiculos_count = Vehiculo.objects.count()
print(f"\nTotal Vehiculos: {vehiculos_count}")
placa_regex = re.compile(r"^[A-Z]{3}-?\d{3}$")
vehiculos_invalidos = 0
for v in Vehiculo.objects.all():
    placa_clean = v.placa.strip().upper()
    if not placa_regex.match(placa_clean):
        print(f"  [ALERTA VEHICULO] Placa no conforme: pk={v.pk}, placa='{v.placa}'")
        vehiculos_invalidos += 1
print(f"Vehiculos con placa no conforme al nuevo validador: {vehiculos_invalidos}")

# 4. Entregas
entregas_count = Entrega.objects.count()
print(f"\nTotal Entregas: {entregas_count}")
estados_entrega_validos = {c[0] for c in Entrega.ESTADOS}
entregas_invalidas = 0
for e in Entrega.objects.all():
    if e.estado not in estados_entrega_validos:
        print(f"  [ALERTA ENTREGA] Estado invalido: pk={e.pk}, estado='{e.estado}'")
        entregas_invalidas += 1
print(f"Entregas con estado invalido: {entregas_invalidas}")

# 5. Usuarios con foto_perfil
usuarios_con_foto = Usuario.objects.exclude(foto_perfil="").exclude(foto_perfil__isnull=True).count()
print(f"\nTotal Usuarios con foto_perfil: {usuarios_con_foto}")

print("\n=== FIN DE VERIFICACIÓN DE SOLO LECTURA ===")
