

from django.utils import timezone
from django.db.models import Sum, Count
import requests
import json
import re
import random
import time
from datetime import datetime
from ..models import (
    ConversationHistory, 
    ConversationMessage, 
    UserFeedback, 
    AIPromptTemplate, 
    AIConfiguration,
    KnowledgeBase
)

# Configuración de Ollama
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"

def verificar_conexion_ollama():
    """Verifica si Ollama está disponible"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return response.status_code == 200
    except Exception as e:
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

def get_conversation(usuario, session_id=None):
    """Obtiene o crea una conversación"""
    if usuario and usuario.is_authenticated:
        conversation, created = ConversationHistory.objects.get_or_create(
            user=usuario,
            session_id=session_id
        )
    else:
        conversation, created = ConversationHistory.objects.get_or_create(
            session_id=session_id or "anonymous"
        )
    return conversation

def add_message_to_conversation(conversation, role, content, prompt_used=None, model_used=None, response_time=None):
    """Agrega un mensaje a la conversación"""
    message = ConversationMessage.objects.create(
        conversation=conversation,
        role=role,
        content=content,
        prompt_used=prompt_used,
        model_used=model_used,
        response_time=response_time
    )
    return message

def check_knowledge_base(mensaje):
    """Verifica la base de conocimiento para respuestas rápidas"""
    mensaje_lower = mensaje.lower()
    kb_entries = KnowledgeBase.objects.filter(success_count__gte=1).order_by('-success_count', '-usage_count')
    
    for entry in kb_entries:
        try:
            if re.search(entry.question_pattern, mensaje_lower, re.IGNORECASE):
                entry.usage_count += 1
                entry.save()
                return entry
        except:
            continue
    return None

def evaluar_expresion_matematica(expr):
    """Evalúa expresiones matemáticas de forma segura, con soporte para álgebra y cálculos avanzados"""
    import math
    from decimal import Decimal, getcontext
    getcontext().prec = 20
    
    expr_original = expr.strip()
    expr_limpia = expr_original.lower()
    
    # Diccionario de funciones matemáticas seguras
    math_funcs = {
        'pi': math.pi,
        'π': math.pi,
        'e': math.e,
        'sen': math.sin,
        'sin': math.sin,
        'cos': math.cos,
        'coseno': math.cos,
        'tan': math.tan,
        'tangente': math.tan,
        'asin': math.asin,
        'acos': math.acos,
        'atan': math.atan,
        'log': math.log10,
        'ln': math.log,
        'logaritmo': math.log10,
        'sqrt': math.sqrt,
        'raiz': math.sqrt,
        'raíz': math.sqrt,
        'abs': abs,
        'factorial': math.factorial,
        'fact': math.factorial,
        'pow': pow,
        'potencia': pow,
        'exp': math.exp,
        'round': round,
    }
    
    # Reemplazar palabras por símbolos y normalizar
    reemplazos = {
        'más': '+',
        'mas': '+',
        'plus': '+',
        'menos': '-',
        'minus': '-',
        'por': '*',
        'multiplicado por': '*',
        'times': '*',
        'dividido por': '/',
        'entre': '/',
        'x': '*',
        '×': '*',
        '÷': '/',
        '^': '**',
        '²': '**2',
        '³': '**3',
        '⁴': '**4',
        '⁵': '**5',
        '⁶': '**6',
        '⁷': '**7',
        '⁸': '**8',
        '⁹': '**9',
        '⁰': '**0',
        ',': '.',
        'al cuadrado': '**2',
        'al cubo': '**3',
        'cuadrado de': '**2',
        'cubo de': '**3',
        'raíz cuadrada de': 'sqrt(',
        'raiz cuadrada de': 'sqrt(',
        'seno de': 'sen(',
        'coseno de': 'cos(',
        'tangente de': 'tan(',
    }
    
    for palabra, reemplazo in reemplazos.items():
        expr_limpia = expr_limpia.replace(palabra, reemplazo)
    
    # Función para manejar "raíz de N
    # Insertar paréntesis donde sea necesario
    def manejar_raiz(match):
        num = match.group(1).strip()
        return f'sqrt({num})'
    
    # Patrones para detectar "raíz de x, raíz cuadrada de x, etc.
    patterns_raiz = [
        r'ra[íi]z (?:cuadrada )?de ([\d\.]+)',
        r'ra[íi]z ([\d\.]+)',
    ]
    
    for p in patterns_raiz:
        expr_limpia = re.sub(p, manejar_raiz, expr_limpia, flags=re.IGNORECASE)
    
    # Ahora intentamos evaluar la expresión de forma segura
    try:
        # Primero intentamos una aproximación
        # Reemplazar espacios que faltantes entre números y paréntesis
        expr_final = expr_limpia
        
        # Manejar casos comunes de álgebra básica (ej: "5x, 3(x+2), etc.
        # Patrón para "número seguido de x (ej: 5x)
        def manejar_mult_x(match):
            num = match.group(1)
            var = match.group(2)
            return f'{num}*{var}'
        
        expr_final = re.sub(r'(\d+)([a-zA-Z])', manejar_mult_x, expr_final)
        
        # Ahora evaluar la expresión matemática
        # Usar eval con un diccionario de contexto seguro
        safe_dict = {
            '__builtins__': None,
            **math_funcs,
        }
        
        # Intentar evaluar
        resultado = eval(expr_final, safe_dict, {})
        
        # Formatear el resultado
        if isinstance(resultado, (int, float)):
            es_entero = False
            if hasattr(resultado, 'is_integer'):
                es_entero = resultado.is_integer()
            if es_entero:
                resultado_entero = int(resultado)
                return f"El resultado de {expr_original} es {resultado_entero}."
            else:
                # Redondear a 6 decimales max
                resultado_redondeado = round(resultado, 6)
                return f"El resultado de {expr_original} es {resultado_redondeado}."
        else:
            return f"El resultado de {expr_original} es {resultado}."
    except:
        # Si eval falló, intentamos un enfoque más simple
        # Buscamos operaciones básicas (5+5, 5-5, etc.)
        operadores = [
            (r'(\d+\.?\d*)\s*\+\s*(\d+\.?\d*)', '+', lambda a,b: a+b),
            (r'(\d+\.?\d*)\s*\-\s*(\d+\.?\d*)', '-', lambda a,b: a-b),
            (r'(\d+\.?\d*)\s*\*\s*(\d+\.?\d*)', '*', lambda a,b: a*b),
            (r'(\d+\.?\d*)\s*\/\s*(\d+\.?\d*)', '/', lambda a,b: a/b),
            (r'(\d+\.?\d*)\s*\^\s*(\d+\.?\d*)', '^', lambda a,b: a**b),
            (r'(\d+\.?\d*)\s*\*\*\s*(\d+\.?\d*)', '**', lambda a,b: a**b),
        ]
        
        for patron, simbolo, func in operadores:
            match = re.search(patron, expr_limpia)
            if match:
                try:
                    num1 = float(match.group(1))
                    num2 = float(match.group(2))
                    if simbolo == '/' and num2 == 0:
                        return "No se puede dividir entre cero."
                    res = func(num1, num2)
                    if res.is_integer():
                        res = int(res)
                    return f"El resultado es {res}."
                except:
                    pass
        
        return None

def update_knowledge_base(mensaje, respuesta, feedback):
    """Actualiza la base de conocimiento con feedback positivo"""
    if feedback == 'good':
        mensaje_lower = mensaje.lower()
        pattern = re.escape(mensaje_lower)
        
        kb_entry, created = KnowledgeBase.objects.get_or_create(
            question_pattern=pattern,
            defaults={'best_response': respuesta}
        )
        
        if not created:
            kb_entry.success_count += 1
            kb_entry.best_response = respuesta
        else:
            kb_entry.success_count = 1
            kb_entry.usage_count = 1
        kb_entry.save()

def get_best_prompt_template():
    """Obtiene la mejor plantilla de prompt basada en éxito"""
    templates = AIPromptTemplate.objects.filter(is_active=True).order_by('-success_rate', '-usage_count')
    if templates.exists():
        return templates.first()
    return None

def preguntar_ia(mensaje, usuario=None, historial=None, session_id=None):
    """Función principal para interactuar con la IA - Mejorada con aprendizaje"""
    if historial is None:
        historial = []
    
    start_time = time.time()
    
    # Obtener o crear conversación
    conversation = get_conversation(usuario, session_id)
    
    # Obtener datos del sistema
    datos = obtener_contexto_datos()
    
    # Personalizar con información del usuario
    nombre_usuario = ""
    if usuario and usuario.is_authenticated:
        nombre_usuario = f"{usuario.nombres} {usuario.apellidos}"
    
    # 1. Primero verificar la base de conocimiento (rápida y aprendida)
    kb_entry = check_knowledge_base(mensaje)
    if kb_entry:
        response_time = time.time() - start_time
        add_message_to_conversation(conversation, 'user', mensaje)
        bot_message = add_message_to_conversation(
            conversation, 'assistant', kb_entry.best_response,
            prompt_used="Knowledge Base",
            model_used="Knowledge Base",
            response_time=response_time
        )
        return kb_entry.best_response, bot_message.id
    
    # 2. Verificar preguntas específicas
    respuesta_especifica = verificar_pregunta_especifica(mensaje, usuario, historial, datos)
    if respuesta_especifica:
        response_time = time.time() - start_time
        add_message_to_conversation(conversation, 'user', mensaje)
        bot_message = add_message_to_conversation(
            conversation, 'assistant', respuesta_especifica,
            prompt_used="Rule-Based",
            model_used="Rule-Based",
            response_time=response_time
        )
        return respuesta_especifica, bot_message.id
    
    # 3. Usar Ollama con la mejor plantilla
    if verificar_conexion_ollama():
        try:
            respuesta_ollama, prompt_used = preguntar_ollama(mensaje, datos, nombre_usuario, historial)
            if respuesta_ollama:
                response_time = time.time() - start_time
                add_message_to_conversation(conversation, 'user', mensaje)
                bot_message = add_message_to_conversation(
                    conversation, 'assistant', respuesta_ollama,
                    prompt_used=prompt_used,
                    model_used=OLLAMA_MODEL,
                    response_time=response_time
                )
                return respuesta_ollama, bot_message.id
        except Exception as e:
            pass
    
    # 4. Último recurso
    respuesta_default = obtener_respuesta_inteligente(mensaje, usuario, historial, datos)
    response_time = time.time() - start_time
    add_message_to_conversation(conversation, 'user', mensaje)
    bot_message = add_message_to_conversation(
        conversation, 'assistant', respuesta_default,
        prompt_used="Default",
        model_used="Default",
        response_time=response_time
    )
    return respuesta_default, bot_message.id

def verificar_pregunta_especifica(mensaje, usuario, historial, datos):
    """Verifica si la pregunta es específica y devuelve la respuesta"""
    mensaje_lower = mensaje.lower()
    es_primera_interaccion = len(historial) == 0
    
    # Construir saludo
    saludo = ""
    es_saludo = any(palabra in mensaje_lower for palabra in ["hola", "buenos días", "buenas tardes", "buenas noches", "qué tal", "cómo estás", "como estas", "buen día", "hey", "holi", "holis"])
    if es_primera_interaccion or es_saludo:
        saludo = "¡Hola!"
        if usuario and usuario.is_authenticated:
            saludo = f"¡Hola {usuario.nombres}!"
    
    # 1. HORA ACTUAL
    palabras_clave_hora = ["qué hora es", "que hora es", "qué horas son", "que horas son", "dime la hora", "hora actual", "hora por favor"]
    if any(palabra in mensaje_lower for palabra in palabras_clave_hora):
        ahora = datetime.now()
        hora_str = ahora.strftime("%H:%M")
        fecha_str = ahora.strftime("%d/%m/%Y")
        return f"{saludo} La hora actual es {hora_str} y la fecha es {fecha_str}.".strip()
    
    # 2. OPERACIONES MATEMÁTICAS - MEJORADAS Y COMPLETAS
    # Primero, extraemos cualquier expresión matemática del mensaje
    try:
        # Buscar expresiones matemáticas (números, operadores, paréntesis)
        # Patrón para detectar expresiones matemáticas completas
        math_patterns = [
            # Preguntas explícitas de cálculo
            (r'cuá?nto es\s+(.+)', 1),
            (r'calcula\s+(.+)', 1),
            (r'resuelve\s+(.+)', 1),
            (r'qué es\s+(.+)', 1),
            (r'cuál es\s+(.+)', 1),
            (r'(.+)\s*=\s*\?', 1),
        ]
        
        for patron, g_idx in math_patterns:
            match = re.search(patron, mensaje_lower)
            if match:
                expr = match.group(g_idx).strip()
                resultado = evaluar_expresion_matematica(expr)
                if resultado is not None:
                    return f"{saludo} {resultado}".strip()
        
        # Si no hay pregunta explícita, intentamos evaluar directamente si parece matemática
        # (contiene números y operadores o palabras matemáticas)
        tiene_numeros = bool(re.search(r'\d+', mensaje_lower))
        tiene_operadores = bool(re.search(r'[+\-*/^%]|más|menos|por|dividido|entre|potencia|raíz|raiz|seno|coseno|tangente|logaritmo|log', mensaje_lower))
        
        if tiene_numeros and (tiene_operadores or len(re.findall(r'\d+', mensaje_lower)) >= 2):
            resultado = evaluar_expresion_matematica(mensaje)
            if resultado is not None:
                return f"{saludo} {resultado}".strip()
    except Exception as e:
        pass
    
    # 3. ALERTAS DE MATERIALES
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
    
    # 4. VEHICULOS DISPONIBLES
    palabras_clave_vehiculos = [
        "vehículos disponibles", "vehiculos disponibles", "qué vehículos están disponibles", "que vehiculos estan disponibles", 
        "autos disponibles", "camiones disponibles", "vehiculos libres", "vehículos libres"
    ]
    if any(palabra in mensaje_lower for palabra in palabras_clave_vehiculos):
        return f"{saludo} Actualmente hay {datos['vehiculos_disponibles']} vehículos disponibles, {datos['vehiculos_en_ruta']} en ruta y {datos['vehiculos_sin_conductor']} sin conductor asignado. En total hay {datos['vehiculos_count']} vehículos en el sistema.".strip()
    
    # 5. PEDIDOS
    palabras_clave_pedidos = [
        "pedidos pendientes", "cuántos pedidos hay", "cuantos pedidos hay", "qué pedidos hay", "que pedidos hay", 
        "estado de pedidos", "pedidos totales"
    ]
    if any(palabra in mensaje_lower for palabra in palabras_clave_pedidos):
        return f"{saludo} Resumen de pedidos: {datos['pedidos_totales']} totales, {datos['pedidos_pendientes']} pendientes, {datos['pedidos_aprobados']} aprobados, {datos['pedidos_en_camino']} en camino, {datos['pedidos_entregados']} entregados y {datos['pedidos_cancelados']} cancelados.".strip()
    
    # 6. DATOS GENERALES DEL SISTEMA
    palabras_clave_sistema = [
        "dime sobre el sistema", "resumen del sistema", "qué hay en el sistema", "que hay en el sistema", 
        "cuántos usuarios hay", "cuantos usuarios hay", "cuántos clientes hay", "cuantos clientes hay", 
        "cuántos proveedores hay", "cuantos proveedores hay"
    ]
    if any(palabra in mensaje_lower for palabra in palabras_clave_sistema):
        return f"{saludo} Resumen del sistema Constru-Trans: {datos['total_usuarios']} usuarios, {datos['clientes_registrados']} clientes, {datos['proveedores_count']} proveedores, {datos['total_materiales']} tipos de materiales, {datos['vehiculos_count']} vehículos y {datos['pedidos_totales']} pedidos.".strip()
    
    # Si no es ninguna de las anteriores, retorna None para que use Ollama
    return None

def preguntar_ollama(mensaje, contexto, nombre_usuario, historial):
    """Pregunta a Ollama usando la API directamente - Mejorada con plantillas"""
    contexto_texto = "\n".join([f"- {k}: {v}" for k, v in contexto.items()])
    
    historial_texto = ""
    if historial:
        historial_texto = "\n\nHISTORIAL DE CONVERSACIÓN (últimos mensajes):\n"
        for msg in historial:
            if msg['sender'] == 'user':
                historial_texto += f"USUARIO: {msg['text']}\n"
            else:
                historial_texto += f"ASISTENTE: {msg['text']}\n"
    
    # Obtener la mejor plantilla o usar la predeterminada
    best_template = get_best_prompt_template()
    template_name = "Default Template"
    
    if best_template:
        system_prompt = best_template.template
        template_name = best_template.name
        best_template.usage_count += 1
        best_template.save()
    else:
        system_prompt = f"""Eres el ASISTENTE VIRTUAL OFICIAL DE CONSTRU-TRANS, una empresa de gestión de materiales de construcción y transporte.

TU ESPECIALIDADES:
1. CÁLCULOS MATEMÁTICOS y ÁLGEBRA - Resuelve cualquier problema matemático (básico, álgebra, geometría, funciones, derivadas, integrales, trigonometría, etc.)
2. Datos del sistema Constru-Trans (pedidos, inventario, vehículos, etc.)
3. Cualquier otra pregunta del usuario (cultura, consejos, etc.)

Tu personalidad:
- Amigable, servicial y profesional
- Respondes en español claro y conciso
- Tienes acceso a todos los datos del sistema Constru-Trans

REGLAS MUY IMPORTANTES:
1. Prioriza responder en español SIEMPRE
2. SI EL USUARIO PREGUNTA SOBRE CÁLCULOS, MATEMÁTICAS o ÁLGEBRA:
   - Resuelve el problema de forma detallada, paso a paso
   - Da el resultado final de forma clara
   - Si es una fórmula, explica cómo funciona
3. Si el usuario pregunta sobre Datos del sistema: Usa los datos proporcionados
4. Si el usuario pregunta sobre cualquier otra cosa: Responde de forma natural y útil
5. Usa el historial para mantener la coherencia
6. NO te quedes callado ni respondas "¿Podrías ser más específico?". ¡Siempre responde algo útil!
7. Responde a TODO, no te niegues a nada que no sea inapropiado
8. Sé creativo y útil

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
        "num_predict": 2000
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
                return respuesta.strip(), template_name
            else:
                return "Claro, cuéntame más sobre lo que necesitas.", template_name
        else:
            return "Claro, cuéntame más sobre lo que necesitas.", template_name
    except Exception as e:
        return "Claro, cuéntame más sobre lo que necesitas.", template_name

def obtener_respuesta_inteligente(mensaje, usuario=None, historial=None, datos=None):
    """Obtiene una respuesta genérica cuando Ollama no está disponible"""
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
        "Estoy aquí para ayudarte. ¿En qué puedo asistirte hoy?",
        "Claro, cuéntame más sobre lo que necesitas.",
        "Estoy listo para ayudarte. ¿Qué te gustaría consultar?",
        "Cuéntame, ¿qué necesitas hoy?",
        "¿En qué puedo ayudarte?",
    ]
    
    return f"{saludo} {random.choice(respuestas_por_defecto)}".strip()

def save_feedback(message_id, feedback, comment=None, user=None):
    """Guarda el feedback y actualiza la base de conocimiento"""
    try:
        message = ConversationMessage.objects.get(id=message_id)
        
        # Crear feedback
        fb = UserFeedback.objects.create(
            message=message,
            user=user,
            feedback=feedback,
            comment=comment
        )
        
        # Actualizar la base de conocimiento si es positivo
        user_message = message.conversation.messages.filter(role='user').order_by('-timestamp').first()
        if user_message:
            update_knowledge_base(user_message.content, message.content, feedback)
        
        # Actualizar tasa de éxito de plantillas
        for template in AIPromptTemplate.objects.filter(is_active=True):
            template.update_success_rate()
        
        return True
    except Exception as e:
        return False

def auto_optimize_prompts():
    """Auto-optimiza prompts basado en feedback"""
    # Obtener plantillas con bajo rendimiento
    low_performing = AIPromptTemplate.objects.filter(
        is_active=True,
        success_rate__lt=50,
        usage_count__gt=5
    )
    
    for template in low_performing:
        # Desactivar plantillas de bajo rendimiento
        template.is_active = False
        template.save()
    
    # Crear nuevas plantillas basadas en feedback positivo
    good_feedback = UserFeedback.objects.filter(feedback='good').select_related('message')[:20]
    for fb in good_feedback:
        if fb.message and fb.message.prompt_used and 'Template' not in fb.message.prompt_used:
            # Analizar patrones exitosos (simplificado)
            pass
    
    return True
