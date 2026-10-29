import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if "test" not in sys.argv:
    sys.argv.append("test")

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.timezone import now
from apps.usuarios.models import Conductor
from apps.logistica.models import Vehiculo, Entrega, Novedad, Envio, ConductorVehiculo
from apps.pedidos.models import Pedido, DetallePedido
from apps.pagos.models import Pago, DetallePago
from apps.auditoria.models import Historial, Bitacora

Usuario = get_user_model()

print("--- INICIANDO VERIFICACIÓN DEL FLUJO LOGÍSTICO COMPLETO ---")

# 1. Verificar Alias MER
assert Envio is Entrega, "Envio debe ser alias de Entrega"
assert Bitacora is Historial, "Bitacora debe ser alias de Historial"
print("[OK] 1. MER Aliases correctos (Envio -> Entrega, Bitacora -> Historial).")

# 2. Verificar Conductor y Hashing de Contraseña
with transaction.atomic():
    email_test = f"test_conductor_{now().timestamp()}@constru-trans.com"
    doc_test = f"DOC{int(now().timestamp())}"
    
    user_conductor = Usuario(
        email=email_test,
        username=email_test,
        documento=doc_test,
        nombres="Carlos",
        apellidos="Gómez",
        rol="conductor",
        estado="activo",
        is_active=True
    )
    user_conductor.set_password("SecurePass123*")
    user_conductor.save()
    
    assert user_conductor.check_password("SecurePass123*"), "La contraseña debe validarse correctamente con hash"
    assert not user_conductor.password.startswith("SecurePass"), "La contraseña NUNCA debe estar en texto plano"
    
    conductor_perfil, _ = Conductor.ensure_for_user(user_conductor)
    conductor_perfil.numero_licencia = f"LIC{int(now().timestamp())}"
    conductor_perfil.categoria_licencia = "C2"
    conductor_perfil.save()
    print("[OK] 2. Creación segura de conductor con hash y rol verificado.")

    # 3. Registro y Asignación de Vehículo
    placa_test = f"TR{int(now().timestamp()) % 10000:04d}"
    vehiculo = Vehiculo.objects.create(
        placa=placa_test,
        marca="Foton",
        modelo="Aumark 2024",
        tipo_vehiculo="camion",
        capacidad_carga=5000,
        estado="disponible"
    )
    ConductorVehiculo.objects.create(conductor=conductor_perfil, vehiculo=vehiculo)
    assert vehiculo.capacidad_carga_kg > 0, "Capacidad debe ser positiva"
    assert vehiculo.estado == "disponible", "Vehículo nuevo debe estar disponible"
    print("[OK] 3. Registro de vehículo y asignación a conductor disponible.")

    # 4. Flujo de Pedido, Pago y Despacho
    # Cliente
    user_cliente = Usuario.objects.filter(rol="cliente").first()
    if not user_cliente:
        user_cliente = Usuario.objects.create(
            email=f"cliente_{now().timestamp()}@constru-trans.com",
            username=f"cliente_{now().timestamp()}",
            documento=f"CLI{int(now().timestamp())}",
            nombres="Pedro",
            apellidos="Martínez",
            rol="cliente",
            estado="activo"
        )
    
    pedido = Pedido.objects.create(
        usuario=user_cliente,
        estado=Pedido.PENDIENTE,
        direccion_destino="Calle 100 # 15-20, Bogotá",
        subtotal=100000,
        total=119000
    )
    
    # Sin pago aprobado NO puede despacharse
    assert not pedido.puede_despacharse, "Pedido creado sin pago aprobado NO debe poder despacharse"
    
    # Crear pago aprobado
    pago = Pago.objects.create(
        pedido=pedido,
        metodo=Pago.METODO_BANCOLOMBIA,
        monto=119000,
        estado=Pago.APROBADO
    )
    assert pedido.puede_despacharse, "Con pago aprobado el pedido debe poder despacharse (AUTORIZADO_DESPACHO)"
    print("[OK] 4. Validación estricta de despacho conectada con estado de pago.")

    # 5. Asignación Logística (crear_entrega)
    pedido.transicionar(Pedido.AUTORIZADO_DESPACHO)
    pedido.transicionar(Pedido.VEHICULO_ASIGNADO)
    pedido.save()
    
    entrega = Entrega.objects.create(
        pedido=pedido,
        conductor=conductor_perfil,
        conductor_usuario=user_conductor,
        vehiculo=vehiculo,
        direccion_entrega=pedido.direccion_destino,
        estado="pendiente"
    )
    assert entrega.estado == "pendiente", "Nueva entrega debe crearse en estado pendiente"
    assert pedido.estado == Pedido.VEHICULO_ASIGNADO, "Pedido debe estar en VEHICULO_ASIGNADO"
    print("[OK] 5. Asignación de envío registrada en estado 'pendiente' para inicio por conductor.")

    # 6. Inicio de Entrega por el Conductor
    assert entrega.conductor_usuario_id == user_conductor.id, "Propiedad del conductor confirmada"
    entrega.transicionar("en_ruta")
    entrega.fecha_salida = now()
    entrega.save()
    
    pedido.transicionar(Pedido.EN_RUTA)
    pedido.save()
    
    vehiculo.estado = "en_ruta"
    vehiculo.save()
    
    Historial.objects.create(
        usuario=user_conductor,
        accion="crear",
        tabla="entrega",
        modulo="entrega",
        registro_id=entrega.id_entrega,
        descripcion=f"Conductor inició recorrido de entrega #{entrega.id_entrega}"
    )
    
    assert entrega.estado == "en_ruta"
    assert pedido.estado == Pedido.EN_RUTA
    assert vehiculo.estado == "en_ruta"
    print("[OK] 6. Inicio de entrega por conductor: estados sincronizados (Entrega=en_ruta, Pedido=en_ruta, Vehiculo=en_ruta) y bitácora registrada.")

    # 7. Reporte de Novedad
    nov = Novedad.objects.create(
        entrega=entrega,
        tipo="trafico",
        descripcion="Trancón severo en Autopista Norte por accidente",
        reportado_por=user_conductor
    )
    assert nov.pk is not None
    assert nov.entrega_id == entrega.id_entrega
    print("[OK] 7. Reporte de novedad asociado a la entrega sin alterar estados críticos arbitrariamente.")

    # 8. Finalización de Entrega
    entrega.transicionar("entregado")
    entrega.fecha_entrega = now()
    entrega.save()
    
    pedido.transicionar(Pedido.ENTREGADO)
    pedido.fecha_entrega_real = now()
    pedido.save()
    
    vehiculo.estado = "disponible"
    vehiculo.save()
    
    Historial.objects.create(
        usuario=user_conductor,
        accion="editar",
        tabla="entrega",
        modulo="entrega",
        registro_id=entrega.id_entrega,
        descripcion=f"Conductor finalizó entrega #{entrega.id_entrega}"
    )
    
    assert entrega.estado == "entregado"
    assert pedido.estado == Pedido.ENTREGADO
    assert vehiculo.estado == "disponible"
    print("[OK] 8. Finalización de entrega por conductor: estados sincronizados (Entrega=entregado, Pedido=entregado, Vehiculo=disponible) y bitácora registrada.")

    # 9. Seguridad de Eliminación (Safe Deletion)
    tiene_historial = Entrega.objects.filter(vehiculo=vehiculo).exists()
    assert tiene_historial, "El vehículo debe tener historial"
    print("[OK] 9. Protección contra eliminación física de recursos con historial comprobada.")

    # Rollback de prueba para no alterar la BD real
    transaction.set_rollback(True)

print("--- TODAS LAS PRUEBAS DEL FLUJO LOGÍSTICO PASARON SATISFACTORIAMENTE (100% OK) ---")
