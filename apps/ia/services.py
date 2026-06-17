
from django.utils import timezone
from django.db.models import Sum, Count
import requests
import json

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
    """Función principal para interactuar con la IA"""
    if historial is None:
        historial = []
    
    # Obtener datos del sistema
    datos = obtener_contexto_datos()
    
    # Personalizar con información del usuario
    nombre_usuario = ""
    if usuario and usuario.is_authenticated:
        nombre_usuario = f"{usuario.nombres} {usuario.apellidos}"
    
    # PRIMERO: Intentar con las respuestas DIRECTAS y CONFIABLES
    # Primero revisamos si es una pregunta específica (matemáticas, alertas, etc.)
    respuesta_especifica = verificar_pregunta_especifica(mensaje, usuario, historial, datos)
    if respuesta_especifica:
        return respuesta_especifica
    
    # SI NO ES UNA PREGUNTA ESPECÍFICA: Intentar con Ollama
    if verificar_conexion_ollama():
        try:
            return preguntar_ollama(mensaje, datos, nombre_usuario, historial)
        except Exception as e:
            pass  # Fallback a la respuesta inteligente
    
    # ÚLTIMO RECURSO: Respuesta inteligente genérica
    return obtener_respuesta_inteligente(mensaje, usuario, historial, datos)

def verificar_pregunta_especifica(mensaje, usuario, historial, datos):
    """Verifica si la pregunta es específica y devuelve la respuesta"""
    import re
    import random
    
    mensaje_lower = mensaje.lower()
    es_primera_interaccion = len(historial) == 0
    es_saludo = any(palabra in mensaje_lower for palabra in ["hola", "buenos días", "buenas tardes", "buenas noches", "qué tal", "cómo estás", "como estas", "buen día"])
    
    # Construir saludo
    saludo = ""
    if es_primera_interaccion or es_saludo:
        saludo = "¡Hola!"
        if usuario and usuario.is_authenticated:
            saludo = f"¡Hola {usuario.nombres}!"
    
    # 1. OPERACIONES MATEMÁTICAS
    patron_suma = r'(\d+)\s*(?:\+|más|mas|plus)\s*(\d+)'
    patron_resta = r'(\d+)\s*(?:-|menos|minus)\s*(\d+)'
    patron_multiplicacion = r'(\d+)\s*(?:\*|por|multiplicado por|times)\s*(\d+)'
    patron_division = r'(\d+)\s*(?:\/|dividido por|entre|divided by)\s*(\d+)'
    patron_cuanto_es = r'cu[áa]nto es\s+(\d+)\s*([\+\-\*\/]|más|mas|plus|menos|minus|por|multiplicado por|times|dividido por|entre|divided by)\s*(\d+)'
    
    resultado_matematico = None
    operacion_realizada = ""
    
    # Verificar "cuánto es"
    match_cuanto = re.search(patron_cuanto_es, mensaje_lower)
    if match_cuanto:
        num1 = float(match_cuanto.group(1))
        op = match_cuanto.group(2)
        num2 = float(match_cuanto.group(3))
        if op in ['+', 'más', 'mas', 'plus']:
            resultado_matematico = num1 + num2
            operacion_realizada = f"{num1} + {num2}"
        elif op in ['-', 'menos', 'minus']:
            resultado_matematico = num1 - num2
            operacion_realizada = f"{num1} - {num2}"
        elif op in ['*', 'por', 'multiplicado por', 'times']:
            resultado_matematico = num1 * num2
            operacion_realizada = f"{num1} × {num2}"
        elif op in ['/', 'dividido por', 'entre', 'divided by']:
            if num2 != 0:
                resultado_matematico = num1 / num2
                operacion_realizada = f"{num1} ÷ {num2}"
            else:
                resultado_matematico = None
                operacion_realizada = "Error: no se puede dividir entre cero"
    else:
        # Verificar otras operaciones
        match_suma = re.search(patron_suma, mensaje_lower)
        if match_suma:
            num1, num2 = float(match_suma.group(1)), float(match_suma.group(2))
            resultado_matematico = num1 + num2
            operacion_realizada = f"{num1} + {num2}"
        else:
            match_resta = re.search(patron_resta, mensaje_lower)
            if match_resta:
                num1, num2 = float(match_resta.group(1)), float(match_resta.group(2))
                resultado_matematico = num1 - num2
                operacion_realizada = f"{num1} - {num2}"
            else:
                match_mult = re.search(patron_multiplicacion, mensaje_lower)
                if match_mult:
                    num1, num2 = float(match_mult.group(1)), float(match_mult.group(2))
                    resultado_matematico = num1 * num2
                    operacion_realizada = f"{num1} × {num2}"
                else:
                    match_div = re.search(patron_division, mensaje_lower)
                    if match_div:
                        num1, num2 = float(match_div.group(1)), float(match_div.group(2))
                        if num2 != 0:
                            resultado_matematico = num1 / num2
                            operacion_realizada = f"{num1} ÷ {num2}"
                        else:
                            resultado_matematico = None
                            operacion_realizada = "Error: no se puede dividir entre cero"
    
    if resultado_matematico is not None:
        respuestas_matematicas = [
            f"El resultado de {operacion_realizada} es {resultado_matematico}.",
            f"¡Listo! {operacion_realizada} = {resultado_matematico}.",
            f"El cálculo da {resultado_matematico} ({operacion_realizada}).",
        ]
        return f"{saludo} {random.choice(respuestas_matematicas)}".strip()
    
    # 2. ALERTAS DE MATERIALES
    palabras_clave_alertas = [
        "alerta", "alertas", "poco material", "material bajo", "stock bajo", 
        "qué materiales", "que materiales", "materiales con poco", "materail",
        "acabarse", "terminándose", "terminando", "sin stock", "sin materiales",
        "hay poco", "falta", "faltan"
    ]
    if any(palabra in mensaje_lower for palabra in palabras_clave_alertas):
        if datos['stock_bajo'] > 0:
            respuestas_alertas = [
                f"¡Alerta! Hay {datos['stock_bajo']} materiales con stock bajo. ¡Revisa el inventario!",
                f"Aviso: {datos['stock_bajo']} materiales están por acabarse. ¡No te olvides de reabastecer!",
                f"¡Atención! Hay {datos['stock_bajo']} materiales con stock mínimo. ¡Toma acción!",
            ]
            return f"{saludo} {random.choice(respuestas_alertas)}".strip()
        else:
            return f"{saludo} Todo bien en el inventario! No hay materiales con stock bajo."
    
    # 3. PREGUNTAS ESPECÍFICAS SOBRE EL SISTEMA
    # Vehículos
    if any(palabra in mensaje_lower for palabra in ["vehículo", "vehículos", "vehiculo", "vehiculos", "coche", "camión", "camion", "auto"]):
        if any(palabra in mensaje_lower for palabra in ["sin conductor", "sin asignar", "disponibles"]):
            respuesta = f"Actualmente hay {datos['vehiculos_sin_conductor']} vehículos sin conductor y {datos['vehiculos_disponibles']} disponibles."
        elif any(palabra in mensaje_lower for palabra in ["en ruta", "viajando", "en camino"]):
            respuesta = f"Hay {datos['vehiculos_en_ruta']} vehículos en ruta y {datos['vehiculos_count']} en total."
        else:
            respuesta = f"En el sistema hay {datos['vehiculos_count']} vehículos: {datos['vehiculos_disponibles']} disponibles, {datos['vehiculos_en_ruta']} en ruta y {datos['vehiculos_sin_conductor']} sin conductor."
        return f"{saludo} {respuesta}".strip()
    
    # Conductores
    if any(palabra in mensaje_lower for palabra in ["conductor", "conductores", "chofer", "choferes"]):
        respuesta = f"Actualmente hay {datos['conductor_count']} conductores registrados en el sistema."
        return f"{saludo} {respuesta}".strip()
    
    # Inventario
    if any(palabra in mensaje_lower for palabra in ["inventario", "material", "materiales", "stock", "almacén", "almacen"]):
        if any(palabra in mensaje_lower for palabra in ["bajo", "poco", "escasez", "faltante"]):
            respuesta = f"Hay {datos['stock_bajo']} materiales con stock bajo. El total de materiales es {datos['total_materiales']} con {datos['total_stock']} unidades en stock."
        else:
            respuesta = f"El inventario tiene {datos['total_materiales']} tipos de materiales, con {datos['total_stock']} unidades en total y {datos['stock_bajo']} con stock bajo."
        return f"{saludo} {respuesta}".strip()
    
    # Pedidos
    if any(palabra in mensaje_lower for palabra in ["pedido", "pedidos", "orden", "órdenes", "ordenes"]):
        respuesta = f"Tenemos {datos['pedidos_totales']} pedidos en total: {datos['pedidos_pendientes']} pendientes, {datos['pedidos_aprobados']} aprobados, {datos['pedidos_en_camino']} en camino y {datos['pedidos_entregados']} entregados."
        return f"{saludo} {respuesta}".strip()
    
    # Usuarios
    if any(palabra in mensaje_lower for palabra in ["usuario", "usuarios", "empleado", "empleados", "trabajador", "trabajadores"]):
        respuesta = f"Hay {datos['total_usuarios']} usuarios registrados: {datos['admin_count']} administradores, {datos['cliente_count']} clientes, {datos['conductor_count']} conductores y {datos['empleado_count']} empleados."
        return f"{saludo} {respuesta}".strip()
    
    # Ventas
    if any(palabra in mensaje_lower for palabra in ["venta", "ventas", "factura", "facturas", "dinero", "ganancias"]):
        respuesta = f"Las ventas totales son ${datos['total_ventas']:,.2f}, con {datos['facturas_totales']} facturas (${datos['total_facturado']:,.2f} facturado)."
        return f"{saludo} {respuesta}".strip()
    
    # Si no es ninguna pregunta específica
    return None

def preguntar_ollama(mensaje, contexto, nombre_usuario, historial):
    """Pregunta a Ollama usando la API directamente"""
    # Convertir contexto a texto legible
    contexto_texto = "\n".join([f"- {k}: {v}" for k, v in contexto.items()])
    
    # Convertir historial a texto legible
    historial_texto = ""
    if historial:
        historial_texto = "\n\nHISTORIAL DE LA CONVERSACIÓN:\n"
        for msg in historial:
            if msg['sender'] == 'user':
                historial_texto += f"USUARIO: {msg['text']}\n"
            else:
                historial_texto += f"ASISTENTE: {msg['text']}\n"
    
    # Crear el prompt del sistema
    system_prompt = f"""Eres el ASISTENTE VIRTUAL OFICIAL de la empresa CONSTRU-TRANS, un sistema de gestión de pedidos, inventario y transporte para materiales de construcción.

REGLAS ESTRICTAS:
1. TU ÚNICA MISIÓN: Ayudar a los usuarios del sistema Constru-Trans
2. RESPONDE EN ESPAÑOL, de manera clara y amigable
3. SI EL USUARIO TE PREGUNTA POR DATOS DEL SISTEMA (pedidos, inventario, vehículos, conductores, etc.), usa el CONTEXTO proporcionado para responder con PRECISIÓN
4. SI EL USUARIO TE PREGUNTA ALGO GENERAL (como la hora, qué es Constru-Trans, qué puedes hacer, etc.):
   - RESPONDE DIRECTAMENTE y NATURALMENTE
   - SI NECESITAS USAR EL CONTEXTO, ÚSALO
   - SI ES UNA PREGUNTA GENERAL, RESPONDE SIN PROBLEMAS
5. SI EL USUARIO TE PREGUNTA POR UNA OPERACIÓN MATEMÁTICA (suma, resta, multiplicación, división):
   - CALCULA y RESPONDE con el resultado
6. SI EL USUARIO PREGUNTA POR ALERTAS DE MATERIALES O STOCK BAJO:
   - Usa el CONTEXTO para decir cuántos materiales hay con stock bajo
7. NO INVENTES DATOS que no estén en el contexto
8. SALUDA al usuario por su nombre si lo conoces (solo si es la primera vez o el usuario te dice hola)
9. USA el HISTORIAL DE LA CONVERSACIÓN para responder de manera coherente
10. Haz referencia a mensajes anteriores si es necesario

DATOS DEL USUARIO:
- Nombre: {nombre_usuario if nombre_usuario else "No registrado"}

CONTEXTO ACTUAL DEL SISTEMA CONSTRU-TRANS:
{contexto_texto}
{historial_texto}"""

    # Construir la solicitud a Ollama
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": mensaje,
        "system": system_prompt,
        "stream": False,
        "temperature": 0.7,
        "num_predict": 1024
    }
    
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "Lo siento, no pude procesar tu solicitud en este momento.")
        else:
            return obtener_respuesta_inteligente(mensaje, None, historial, contexto)
    except Exception as e:
        return obtener_respuesta_inteligente(mensaje, None, historial, contexto)

def obtener_respuesta_inteligente(mensaje, usuario=None, historial=None, datos=None):
    """Obtiene una respuesta genérica cuando no es una pregunta específica"""
    import random
    from django.utils import timezone
    
    if historial is None:
        historial = []
    
    if datos is None:
        datos = obtener_contexto_datos()
    
    # Verificar si es la primera interacción
    es_primera_interaccion = len(historial) == 0
    
    # Convertir mensaje a minúsculas para mejor detección
    mensaje_lower = mensaje.lower()
    es_saludo = any(palabra in mensaje_lower for palabra in ["hola", "buenos días", "buenas tardes", "buenas noches", "qué tal", "cómo estás", "como estas", "buen día"])
    
    # Construir saludo
    saludo = ""
    if es_primera_interaccion or es_saludo:
        saludo = "¡Hola!"
        if usuario and usuario.is_authenticated:
            saludo = f"¡Hola {usuario.nombres}!"
    
    # --- SALUDOS Y BIENVENIDAS ---
    if es_saludo:
        return f"{saludo} Soy tu asistente virtual de Constru-Trans. ¿En qué puedo ayudarte hoy? Puedo darte información sobre inventario, pedidos, vehículos, conductores y más!"
    
    # --- AYUDA ---
    if any(palabra in mensaje_lower for palabra in ["ayuda", "ayúdame", "ayudame", "qué puedes hacer", "que puedes hacer", "qué haces", "que haces", "qué sabes", "que sabes"]):
        respuesta = "Estoy aquí para ayudarte con todo lo relacionado al sistema Constru-Trans. Puedes preguntarme sobre:\n- Estado de pedidos\n- Inventario y materiales\n- Vehículos y conductores\n- Ventas y facturas\n- Usuarios del sistema\n- Realizar cálculos matemáticos\n\n¿Qué necesitas?"
        return f"{saludo} {respuesta}".strip()
    
    # --- PREGUNTAS SOBRE CONSTRU-TRANS ---
    if any(palabra in mensaje_lower for palabra in ["qué es", "que es", "qué es constru-trans", "que es constru-trans", "de qué se trata", "de que se trata"]):
        respuestas = [
            "Constru-Trans es un sistema de gestión para materiales de construcción. Te ayuda a administrar pedidos, inventario, vehículos y más.",
            "Somos un sistema de gestión de pedidos y transporte para materiales de construcción. ¡Puedo ayudarte con todo!",
        ]
        return f"{saludo} {random.choice(respuestas)}".strip()
    
    # --- PREGUNTAS SOBRE HORA ---
    if any(palabra in mensaje_lower for palabra in ["hora", "horas", "qué hora", "que hora", "tiempo"]):
        ahora = timezone.localtime()
        hora_actual = ahora.strftime("%H:%M")
        fecha_actual = ahora.strftime("%d/%m/%Y")
        respuestas = [
            f"Son las {hora_actual} del {fecha_actual}.",
            f"Ahora mismo son las {hora_actual} (fecha: {fecha_actual}).",
        ]
        return f"{saludo} {random.choice(respuestas)}".strip()
    
    # --- RESPUESTA POR DEFECTO ---
    respuestas = [
        f"Claro, te cuento: hay {datos['pedidos_totales']} pedidos, {datos['total_materiales']} materiales y {datos['vehiculos_count']} vehículos. ¿Necesitas información específica?",
        f"Actualmente tenemos {datos['pedidos_pendientes']} pedidos pendientes y {datos['vehiculos_disponibles']} vehículos disponibles. ¿Qué necesitas?",
        f"Puedo ayudarte con información sobre pedidos, inventario, vehículos y más. ¿Qué te interesa saber?",
        f"Cuéntame qué necesitas y estaré encantado de ayudarte con información del sistema.",
        "¿Podrías ser más específico? Puedo ayudarte con pedidos, inventario, vehículos, facturas y más.",
        "¿De qué te gustaría hablar? Tengo información sobre todo el sistema Constru-Trans."
    ]
    
    respuesta = random.choice(respuestas)
    return f"{saludo} {respuesta}".strip()

