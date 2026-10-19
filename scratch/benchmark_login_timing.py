import os
import sys
import time
import statistics

sys.path.insert(0, os.getcwd())
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

from django.conf import settings
from django.contrib.auth.hashers import make_password, get_hasher
from django.test import Client
from django.test.runner import DiscoverRunner
from django.core.cache import cache

print("=" * 80)
print("BENCHMARK DE AUTENTICACIÓN Y RESISTENCIA A TIMING ATTACKS")
print("=" * 80)

# 1. Hasher efectivo
active_hasher = get_hasher()
print(f"1. Hasher Activo Efectivo: {active_hasher}")
print(f"   Lista PASSWORD_HASHERS: {settings.PASSWORD_HASHERS}")

# 2. Medición de una sola llamada a make_password()
t0 = time.perf_counter()
single_hash = make_password("PruebaVelocidad123*")
t1 = time.perf_counter()
single_call_ms = (t1 - t0) * 1000
print(f"2. Tiempo de 1 llamada individual a make_password(): {single_call_ms:.2f} ms")
print(f"   Prefijo del hash generado: {single_hash[:35]}...\n")

# 3. Setup de BD de pruebas e inserción de usuario con hash Argon2
runner = DiscoverRunner(verbosity=0)
old_config = runner.setup_databases()

from apps.usuarios.models import Usuario

u, created = Usuario.objects.get_or_create(
    username="usuario_bench_existente",
    defaults={
        "email": "bench_existente@test.com",
        "nombres": "Bench",
        "apellidos": "User",
        "documento": "99887766",
        "tipo_documento": "CC",
        "rol": "cliente",
        "is_active": True,
        "estado": "activo"
    }
)
u.set_password("PasswordValido123*")
u.save()

# Usuario bloqueado
u_bloqueado, _ = Usuario.objects.get_or_create(
    username="usuario_bench_bloqueado",
    defaults={
        "email": "bench_bloqueado@test.com",
        "nombres": "Bench",
        "apellidos": "Bloqueado",
        "documento": "99887755",
        "tipo_documento": "CC",
        "rol": "cliente",
        "is_active": True,
        "estado": "bloqueado",
        "intentos_fallidos": 5
    }
)
u_bloqueado.set_password("PasswordValido123*")
u_bloqueado.save()

client = Client()

# Warm-up (2 peticiones)
client.post('/usuarios/login/', {'username': 'usuario_bench_existente', 'password': 'PasswordErroneoWarm1*', 'captcha': 'on'}, REMOTE_ADDR='192.168.1.10')
client.post('/usuarios/login/', {'username': 'usuario_inexistente_warm', 'password': 'PasswordErroneoWarm1*', 'captcha': 'on'}, REMOTE_ADDR='192.168.1.11')

N = 35  # Más de 30 intentos por caso

tiempos_existente = []
resp_existente_content = None
print(f"3. Ejecutando {N} intentos con USUARIO EXISTENTE (password errónea):")
for i in range(N):
    cache.clear()
    t_start = time.perf_counter()
    resp = client.post(
        '/usuarios/login/',
        {'username': 'usuario_bench_existente', 'password': f'PasswordErroneo{i}*', 'captcha': 'on'},
        REMOTE_ADDR=f'192.168.2.{(i % 250) + 1}'
    )
    t_end = time.perf_counter()
    ms = (t_end - t_start) * 1000
    tiempos_existente.append(ms)
    assert resp.status_code == 400, f"Status inesperado: {resp.status_code}"
    resp_existente_content = resp.content
    print(f"   Intento {i+1:2d}: {ms:6.2f} ms | Status: {resp.status_code}")

tiempos_inexistente = []
resp_inexistente_content = None
print(f"\n4. Ejecutando {N} intentos con USUARIO INEXISTENTE:")
for i in range(N):
    cache.clear()
    t_start = time.perf_counter()
    resp = client.post(
        '/usuarios/login/',
        {'username': f'usuario_no_existe_{i}_{time.time_ns()}', 'password': f'PasswordErroneo{i}*', 'captcha': 'on'},
        REMOTE_ADDR=f'192.168.3.{(i % 250) + 1}'
    )
    t_end = time.perf_counter()
    ms = (t_end - t_start) * 1000
    tiempos_inexistente.append(ms)
    assert resp.status_code == 400, f"Status inesperado: {resp.status_code}"
    resp_inexistente_content = resp.content
    print(f"   Intento {i+1:2d}: {ms:6.2f} ms | Status: {resp.status_code}")

tiempos_bloqueado = []
resp_bloqueado_content = None
print(f"\n5. Ejecutando {N} intentos con USUARIO BLOQUEADO:")
for i in range(N):
    cache.clear()
    t_start = time.perf_counter()
    resp = client.post(
        '/usuarios/login/',
        {'username': 'usuario_bench_bloqueado', 'password': f'PasswordErroneo{i}*', 'captcha': 'on'},
        REMOTE_ADDR=f'192.168.4.{(i % 250) + 1}'
    )
    t_end = time.perf_counter()
    ms = (t_end - t_start) * 1000
    tiempos_bloqueado.append(ms)
    assert resp.status_code == 400, f"Status inesperado: {resp.status_code}"
    resp_bloqueado_content = resp.content
    print(f"   Intento {i+1:2d}: {ms:6.2f} ms | Status: {resp.status_code}")

# Teardown
runner.teardown_databases(old_config)

mean_exist = statistics.mean(tiempos_existente)
mean_inexist = statistics.mean(tiempos_inexistente)
mean_bloq = statistics.mean(tiempos_bloqueado)

print("\n" + "=" * 80)
print("RESUMEN ESTADÍSTICO DE TIEMPOS (ARGON2 REAL):")
print("=" * 80)
print(f"Usuario Existente (erróneo): Promedio = {mean_exist:6.2f} ms | Mediana = {statistics.median(tiempos_existente):6.2f} ms | StdDev = {statistics.stdev(tiempos_existente):4.2f} ms")
print(f"Usuario Inexistente:          Promedio = {mean_inexist:6.2f} ms | Mediana = {statistics.median(tiempos_inexistente):6.2f} ms | StdDev = {statistics.stdev(tiempos_inexistente):4.2f} ms")
print(f"Usuario Bloqueado:            Promedio = {mean_bloq:6.2f} ms | Mediana = {statistics.median(tiempos_bloqueado):6.2f} ms | StdDev = {statistics.stdev(tiempos_bloqueado):4.2f} ms")
print(f"Diferencia |Existente - Inexistente|: {abs(mean_exist - mean_inexist):.2f} ms")
print(f"Diferencia |Bloqueado - Inexistente|: {abs(mean_bloq - mean_inexist):.2f} ms")
print("\nVerificación de respuestas indistinguibles:")
print(f"Mensaje en respuesta Existente contiene 'Usuario o contraseña incorrectos': {'Usuario o contrase' in resp_existente_content.decode('utf-8', errors='ignore')}")
print(f"Mensaje en respuesta Inexistente contiene 'Usuario o contraseña incorrectos': {'Usuario o contrase' in resp_inexistente_content.decode('utf-8', errors='ignore')}")
print(f"Mensaje en respuesta Bloqueado contiene 'Usuario o contraseña incorrectos': {'Usuario o contrase' in resp_bloqueado_content.decode('utf-8', errors='ignore')}")
print(f"¿Existe alguna mención de 'bloqueada' o 'cuenta inactiva' para el atacante?: {'bloquead' in resp_bloqueado_content.decode('utf-8', errors='ignore').lower()}")
