
from django.utils import timezone
from django.db.models import Sum, Count
import requests
import json
import re
import random

# Configuración de Ollama
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"

def verificar_conexion_ollama():
    """Verifica si Ollama está disponible"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def obtener_contexto_datos():
    """Obtiene datos relevantes completos del sistema para la IA"""
    try:
        from apps.usuarios.models import Usuario, MaterialConstruccion, Stock, Proveedor, Vehiculo
        from apps.clientes.models import Cliente
        from apps.gestion_pedidos.models import Pedido as PedidoGestion
        from apps.compras.models import Compra
        from apps.facturacion.models import Factura
        from apps.pagos.models import Pago

        # --- USUARIOS ---
        total_usuarios = Usuario.objects.count()
        usuarios_activos = Usuario.objects.filter(estado='activo').count()
        admin_count = Usuario.objects.filter(rol='admin').count()
        cliente_count = Usuario.objects.filter(rol='cliente').count()
        conductor_count = Usuario.objects.filter(rol='conductor').count()
        empleado_count = Usuario.objects.filter(rol='empleado').count()
        
        # --- INVENTARIO ---
        total_materiales = MaterialConstruccion.objects.count()
        
        try:
            stocks = Stock.objects.all()
            total_stock = sum(s.cantidad_actual for s in stocks)
            stock_bajo = sum(1 for s in stocks if s.cantidad_actual <= s.stock_minimo)
        except:
            total_stock = 0
            stock_bajo = 0
        
        # --- PEDIDOS ---
        try:
            pedidos_totales = PedidoGestion.objects.count()
            pedidos_pendientes = PedidoGestion.objects.filter(estado='pendiente').count()
            pedidos_aprobados = PedidoGestion.objects.filter(estado='aprobado').count()
            pedidos_en_camino = PedidoGestion.objects.filter(estado='en_camino').count()
            pedidos_entregados = PedidoGestion.objects.filter(estado='entregado').count()
            pedidos_cancelados = PedidoGestion.objects.filter(estado='cancelado').count()
            total_ventas = PedidoGestion.objects.aggregate(Sum('total'))['total__sum'] or 0
        except:
            pedidos_totales = 0
            pedidos_pendientes = 0
            pedidos_aprobados = 0
            pedidos_en_camino = 0
            pedidos_entregados = 0
            pedidos_cancelados = 0
            total_ventas = 0
        
        # --- COMPRAS ---
        try:
            compras_totales = Compra.objects.count()
            compras_pendientes = Compra.objects.filter(estado='pendiente').count()
            compras_recibidas = Compra.objects.filter(estado='recibida').count()
            total_compras = Compra.objects.aggregate(Sum('total_compra'))['total_compra__sum'] or 0
        except:
            compras_totales = 0
            compras_pendientes = 0
            compras_recibidas = 0
            total_compras = 0
        
        # --- FACTURAS ---
        try:
            facturas_totales = Factura.objects.count()
            facturas_pendientes = Factura.objects.filter(estado='pendiente').count()
            facturas_pagadas = Factura.objects.filter(estado='pagada').count()
            total_facturado = Factura.objects.aggregate(Sum('total'))['total__sum'] or 0
        except:
            facturas_totales = 0
            facturas_pendientes = 0
            facturas_pagadas = 0
            total_facturado = 0
        
        # --- PAGOS ---
        try:
            pagos_totales = Pago.objects.count()
            total_pagado = Pago.objects.aggregate(Sum('monto'))['monto__sum'] or 0
        except:
            pagos_totales = 0
            total_pagado = 0
        
        # --- PROVEEDORES ---
        try:
            proveedores_count = Proveedor.objects.count()
        except:
            proveedores_count = 0
        
        # --- VEHICULOS ---
        try:
            vehiculos_count = Vehiculo.objects.count()
            vehiculos_disponibles = Vehiculo.objects.filter(estado='disponible').count()
            vehiculos_en_ruta = Vehiculo.objects.filter(estado='en_ruta').count()
            vehiculos_sin_conductor = Vehiculo.objects.filter(conductor__isnull=True).count()
        except:
            vehiculos_count = 0
            vehiculos_disponibles = 0
            vehiculos_en_ruta = 0
            vehiculos_sin_conductor = 0
        
        # --- CLIENTES ---
        try:
            clientes_registrados = Cliente.objects.count()
        except:
            clientes_registrados = 0

        return {
            'total_usuarios': total_usuarios,
            'usuarios_activos': usuarios_activos,
            'admin_count': admin_count,
            'cliente_count': cliente_count,
            'conductor_count': conductor_count,
            'empleado_count': empleado_count,
            'total_materiales': total_materiales,
            'total_stock': total_stock,
            'stock_bajo': stock_bajo,
            'pedidos_totales': pedidos_totales,
            'pedidos_pendientes': pedidos_pendientes,
            'pedidos_aprobados': pedidos_aprobados,
            'pedidos_en_camino': pedidos_en_camino,
            'pedidos_entregados': pedidos_entregados,
            'pedidos_cancelados': pedidos_cancelados,
            'total_ventas': total_ventas,
            'compras_totales': compras_totales,
            'compras_pendientes': compras_pendientes,
            'compras_recibidas': compras_recibidas,
            'total_compras': total_compras,
            'facturas_totales': facturas_totales,
            'facturas_pendientes': facturas_pendientes,
            'facturas_pagadas': facturas_pagadas,
            'total_facturado': total_facturado,
            'pagos_totales': pagos_totales,
            'total_pagado': total_pagado,
            'proveedores_count': proveedores_count,
            'vehiculos_count': vehiculos_count,
            'vehiculos_disponibles': vehiculos_disponibles,
            'vehiculos_en_ruta': vehiculos_en_ruta,
            'vehiculos_sin_conductor': vehiculos_sin_conductor,
            'clientes_registrados': clientes_registrados
        }
    except Exception as e:
        return {}

def preguntar_ia(mensaje, usuario=None, historial=None):
    """Función principal para interactuar con la IA - Prioriza Ollama primero"""
    if historial is None:
        historial = []
    
    # Obtener datos del sistema
    datos = obtener_contexto_datos()
    
    # Personalizar con información del usuario
    nombre_usuario = ""
    if usuario and usuario.is_authenticated:
        nombre_usuario = f"{usuario.nombres} {usuario.apellidos}"
    
    # Intentar primero con Ollama para TODO (para que responda como ChatGPT)
    if verificar_conexion_ollama():
        try:
            # Verificamos si hay que responder matemáticas o alertas directamente primero (fiables y rápidas)
            respuesta_especifica = verificar_pregunta_especifica(mensaje, usuario, historial, datos)
            if respuesta_especifica:
                # Si es matemáticas o alertas de stock, respondemos primero rápido
                return respuesta_especifica
            
            # Todo lo demás con Ollama
            return preguntar_ollama(mensaje, datos, nombre_usuario, historial)
        except Exception as e:
            pass  # Fallback
    
    # Último recurso
    return obtener_respuesta_inteligente(mensaje, usuario, historial, datos)

def verificar_pregunta_especifica(mensaje, usuario, historial, datos):
    """Verifica si la pregunta es específica y devuelve la respuesta - para matemáticas y alertas"""
    mensaje_lower = mensaje.lower()
    es_primera_interaccion = len(historial) == 0
    
    # Construir saludo
    saludo = ""
    es_saludo = any(palabra in mensaje_lower for palabra in ["hola", "buenos días", "buenas tardes", "buenas noches", "qué tal", "cómo estás", "como estas", "buen día", "hey", "holi", "holis"])
    if es_primera_interaccion or es_saludo:
        saludo = "¡Hola!"
        if usuario and usuario.is_authenticated:
            saludo = f"¡Hola {usuario.nombres}!"
    
    # 1. OPERACIONES MATEMÁTICAS (100% fiables)
    operaciones = [
        (r'cuá?nto es\s+(\d+)\s*([+\-*/]|más|mas|plus|menos|minus|por|multiplicado por|times|dividido por|entre)\s*(\d+)', 1, 3, 2),
        (r'(\d+)\s*([+\-*/]|más|mas|plus|menos|minus|por|multiplicado por|times|dividido por|entre)\s*(\d+)', 1, 3, 2)
    ]
    
    for patron, g1, g2, op_idx in operaciones:
        match = re.search(patron, mensaje_lower)
        if match:
            try:
                num1 = float(match.group(g1))
                num2 = float(match.group(g2))
                op = match.group(op_idx).lower()
                
                resultado = None
                operacion = ""
                
                if op in ['+', 'más', 'mas', 'plus']:
                    resultado = num1 + num2
                    operacion = f"{num1} + {num2}"
                elif op in ['-', 'menos', 'minus']:
                    resultado = num1 - num2
                    operacion = f"{num1} - {num2}"
                elif op in ['*', 'por', 'multiplicado por', 'times']:
                    resultado = num1 * num2
                    operacion = f"{num1} × {num2}"
                elif op in ['/', 'dividido por', 'entre']:
                    if num2 == 0:
                        return f"{saludo} No se puede dividir entre cero."
                    resultado = num1 / num2
                    operacion = f"{num1} ÷ {num2}"
                
                if resultado is not None:
                    if resultado.is_integer():
                        resultado = int(resultado)
                    respuestas_matematicas = [
                        f"El resultado de {operacion} es {resultado}.",
                        f"¡Listo! {operacion} = {resultado}.",
                        f"El cálculo da {resultado} ({operacion}).",
                        f"{operacion} es igual a {resultado}.",
                    ]
                    return f"{saludo} {random.choice(respuestas_matematicas)}".strip()
            except:
                pass
    
    # 2. ALERTAS DE MATERIALES (100% fiables)
    palabras_clave_alertas = [
        "alerta", "alertas", "poco material", "material bajo", "stock bajo", 
        "qué materiales", "que materiales", "materiales con poco", "materail",
        "acabarse", "terminándose", "terminando", "sin stock", "sin materiales",
        "hay poco", "falta", "faltan", "aviso", "notificación"
    ]
    if any(palabra in mensaje_lower for palabra in palabras_clave_alertas):
        if datos['stock_bajo'] > 0:
            respuestas_alertas = [
                f"¡Alerta! Hay {datos['stock_bajo']} materiales con stock bajo. ¡Revisa el inventario!",
                f"Aviso: {datos['stock_bajo']} materiales están por acabarse. ¡No te olvides de reabastecer!",
                f"¡Atención! Hay {datos['stock_bajo']} materiales con stock mínimo. ¡Toma acción!",
                f"Encontré {datos['stock_bajo']} materiales con poco stock. ¡Debes reponerlos!",
            ]
            return f"{saludo} {random.choice(respuestas_alertas)}".strip()
        else:
            respuestas_ok = [
                "Todo bien en el inventario! No hay materiales con stock bajo.",
                "Excelente, el inventario está en perfectas condiciones, sin alertas.",
                "No hay materiales con poco stock. Todo está normal.",
            ]
            return f"{saludo} {random.choice(respuestas_ok)}".strip()
    
    # Si no es matemáticas ni alertas, retorna None para que use Ollama
    return None

def preguntar_ollama(mensaje, contexto, nombre_usuario, historial):
    """Pregunta a Ollama usando la API directamente - ChatGPT propio"""
    contexto_texto = "\n".join([f"- {k}: {v}" for k, v in contexto.items()])
    
    historial_texto = ""
    if historial:
        historial_texto = "\n\nHISTORIAL DE CONVERSACIÓN (últimos mensajes):\n"
        for msg in historial:
            if msg['sender'] == 'user':
                historial_texto += f"USUARIO: {msg['text']}\n"
            else:
                historial_texto += f"ASISTENTE: {msg['text']}\n"
    
    system_prompt = f"""Eres el ASISTENTE VIRTUAL OFICIAL DE CONSTRU-TRANS, una empresa de gestión de materiales de construcción y transporte.

Tu misión: Ayudar al usuario en TODO lo que necesite, como ChatGPT pero como asistente propio de la empresa.

Tu personalidad:
- Amigable, servicial y profesional
- Respondes en español claro y conciso
- Tienes acceso a todos los datos del sistema Constru-Trans

REGLAS:
1. Prioriza responder en español SIEMPRE
2. Si el usuario pregunta sobre Datos del sistema (pedidos, inventario, vehículos, facturas, conductores, clientes, usuarios):
   - Usa los datos proporcionados a continuación para responder con precisión
3. Si el usuario pregunta sobre ALGO GENERAL (cualquier cosa, como matemáticas, cultura, consejos, etc.):
   - Responde de forma natural y inteligente
4. Si el usuario quiere calcular algo matemático: hazlo y responde
5. Si el usuario pide ayuda sobre el sistema: explícale cómo funciona Constru-Trans
6. Si el usuario no sabe qué preguntar: sugiere preguntas sobre el sistema
7. Usa el historial para mantener la coherencia

DATOS DEL USUARIO:
- Nombre: {nombre_usuario if nombre_usuario else "No registrado"}

DATOS ACTUALES DEL SISTEMA CONSTRU-TRANS:
{contexto_texto}
{historial_texto}

¡Responde de forma natural y útil!
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": mensaje,
        "system": system_prompt,
        "stream": False,
        "temperature": 0.8,
        "num_predict": 1500
    }
    
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            respuesta = data.get("response", "")
            if respuesta and len(respuesta.strip()) > 0:
                return respuesta.strip()
            else:
                return obtener_respuesta_inteligente(mensaje, None, historial, contexto)
        else:
            return obtener_respuesta_inteligente(mensaje, None, historial, contexto)
    except Exception as e:
        return obtener_respuesta_inteligente(mensaje, None, historial, contexto)

def obtener_respuesta_inteligente(mensaje, usuario=None, historial=None, datos=None):
    """Obtiene una respuesta genérica cuando no es una pregunta específica"""
    if historial is None:
        historial = []
    
    if datos is None:
        datos = obtener_contexto_datos()
    
    es_primera_interaccion = len(historial) == 0
    mensaje_lower = mensaje.lower()
    es_saludo = any(palabra in mensaje_lower for palabra in ["hola", "buenos días", "buenas tardes", "buenas noches", "qué tal", "cómo estás", "como estas", "buen día", "hey", "holi", "holis"])
    
    saludo = ""
    if es_primera_interaccion or es_saludo:
        saludo = "¡Hola!"
        if usuario and usuario.is_authenticated:
            saludo = f"¡Hola {usuario.nombres}!"
    
    if es_saludo:
        respuestas_bienvenida = [
            "Soy tu asistente virtual de Constru-Trans. ¿En qué puedo ayudarte hoy? Puedo darte información sobre inventario, pedidos, vehículos, conductores y más!",
            "¡Qué gusto tenerte aquí! Soy tu asistente de Constru-Trans. ¿Qué necesitas?",
            "Estoy listo para ayudarte con todo lo relacionado al sistema. ¿En qué puedo colaborarte?",
            "¡Bienvenido! ¿Qué necesitas hoy? Puedo ayudarte con pedidos, inventario, facturas y mucho más.",
        ]
        return f"{saludo} {random.choice(respuestas_bienvenida)}".strip()
    
    if any(palabra in mensaje_lower for palabra in ["ayuda", "ayúdame", "ayudame", "qué puedes hacer", "que puedes hacer", "qué haces", "que haces", "qué sabes", "que sabes", "puedes hacer", "que puedo hacer"]):
        respuesta_ayuda = [
            "Estoy aquí para ayudarte con TODO lo que necesites: desde información del sistema Constru-Trans hasta consejos y cálculos. ¿Qué necesitas?",
            "Puedo ayudarte con lo siguiente: datos de pedidos, inventario, vehículos, facturas, pagos, cálculos matemáticos y cualquier cosa que necesites!",
            "Soy tu asistente completo de Constru-Trans! ¡Pregúntame lo que quieras!",
        ]
        return f"{saludo} {random.choice(respuestas_ayuda)}".strip()
    
    respuestas_por_defecto = [
        f"Claro, cuéntame qué necesitas. Actualmente tenemos {datos['pedidos_totales']} pedidos, {datos['total_materiales']} materiales y {datos['vehiculos_count']} vehículos. ¿Qué te interesa?",
        f"Por supuesto. Tenemos {datos['pedidos_pendientes']} pedidos pendientes y {datos['vehiculos_disponibles']} vehículos disponibles. ¿Qué necesitas saber?",
        "Estoy aquí para ayudarte. ¿Podrías ser un poco más específico? Puedo ayudarte con pedidos, inventario, vehículos, facturas, cálculos y más.",
        "Cuéntame, ¿qué necesitas hoy? Puedo darte información de todo el sistema Constru-Trans.",
        "¿Qué te gustaría consultar? Pregúntame lo que necesites.",
    ]
    
    return f"{saludo} {random.choice(respuestas_por_defecto)}".strip()


