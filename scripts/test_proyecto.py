import os
import sys
import subprocess

def print_separator(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def run_command(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print_separator("TESTEO COMPLETO DEL PROYECTO CONSTRU-TRANS")
    
    # Change to project root (parent of scripts directory)
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    
    tests = []
    
    # Test 1: Verificar Python
    print_separator("1. Verificar Python")
    ok, out, err = run_command("python --version")
    tests.append(("Python instalado", ok))
    if ok:
        print(f"OK: {out.strip()}")
    else:
        print(f"ERROR: {err.strip()}")
    
    # Test 2: Verificar entorno virtual
    print_separator("2. Verificar entorno virtual")
    venv_exists = os.path.exists("venv") and os.path.isdir("venv")
    tests.append(("Entorno virtual existe", venv_exists))
    if venv_exists:
        print("OK: Entorno virtual (venv/) encontrado")
    else:
        print("ERROR: No hay entorno virtual (venv/)")
    
    # Test 3: Verificar requirements.txt
    print_separator("3. Verificar requirements.txt")
    req_exists = os.path.exists("requirements.txt")
    tests.append(("requirements.txt existe", req_exists))
    if req_exists:
        print("OK: requirements.txt encontrado")
    else:
        print("ERROR: No hay requirements.txt")
    
    # Test 4: Verificar .env
    print_separator("4. Verificar .env")
    env_exists = os.path.exists(".env")
    tests.append((".env existe", env_exists))
    if env_exists:
        print("OK: .env encontrado")
    else:
        if os.path.exists(".env.example"):
            print("AVISO: .env no existe, pero .env.example sí está disponible")
        else:
            print("ERROR: No hay .env ni .env.example")
    
    # Test 5: Ejecutar django check
    print_separator("5. Ejecutar django check")
    check_ok, check_out, check_err = run_command("venv\\Scripts\\python.exe manage.py check")
    tests.append(("Django check sin errores", check_ok))
    if check_ok:
        print("OK: Django check: No hay errores")
        if check_out.strip():
            print(f"  Salida:\n{check_out}")
    else:
        print("ERROR en Django check")
        print(f"  Salida de error:\n{check_err}")
    
    # Test 6: Verificar que todas las apps estén en INSTALLED_APPS
    print_separator("6. Verificar INSTALLED_APPS")
    try:
        import django
        from django.conf import settings
        # Add project root to sys.path
        sys.path.insert(0, os.getcwd())
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
        django.setup()
        apps_esperadas = [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'apps.usuarios',
            'apps.clientes',
            'apps.ordenes',
            'apps.compras',
            'apps.inventario',
            'apps.facturacion',
            'apps.pagos',
            'apps.reportes',
            'apps.historial',
            'django_extensions',
        ]
        apps_faltantes = [app for app in apps_esperadas if app not in settings.INSTALLED_APPS]
        tests.append(("Todas las apps en INSTALLED_APPS", len(apps_faltantes) == 0))
        if not apps_faltantes:
            print("OK: Todas las apps esperadas están en INSTALLED_APPS")
        else:
            print(f"ERROR: Apps faltantes en INSTALLED_APPS: {', '.join(apps_faltantes)}")
    except Exception as e:
        tests.append(("Verificar INSTALLED_APPS", False))
        print(f"ERROR al verificar INSTALLED_APPS: {e}")
    
    # Test 7: Verificar que los modelos existan
    print_separator("7. Verificar modelos")
    try:
        # Add project root to sys.path
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())
        from apps.usuarios.models import (Rol, Usuario, EPS, Conductor, Vehiculo, 
                                           ConductorVehiculo, Catalogo, Proveedor, 
                                           MaterialConstruccion, Stock, MetodoPago, Notificacion)
        from apps.clientes.models import Cliente
        from apps.ordenes.models import Pedido, DetallePedido, Entrega
        from apps.facturacion.models import Factura
        from apps.pagos.models import Pago
        from apps.compras.models import Compra, DetalleCompra
        from apps.inventario.models import MovimientoInventario
        from apps.reportes.models import Reporte, HistorialReporte
        tests.append(("Todos los modelos importan correctamente", True))
        print("OK: Todos los modelos importan correctamente")
    except Exception as e:
        tests.append(("Todos los modelos importan correctamente", False))
        print(f"ERROR al importar modelos: {e}")
    
    # Resumen final
    print_separator("RESUMEN FINAL")
    print("\nResultados de los tests:")
    for test_name, passed in tests:
        status = "OK" if passed else "ERROR"
        print(f"  {status} - {test_name}")
    
    total = len(tests)
    pasaron = sum(1 for _, passed in tests if passed)
    print(f"\nTotal: {pasaron}/{total} tests pasaron")
    
    if pasaron == total:
        print("\nOK: Todo esta bien! El proyecto esta listo para usar.")
    else:
        print(f"\nAVISO: Hay {total - pasaron} tests que fallaron. Revisa los mensajes arriba.")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
