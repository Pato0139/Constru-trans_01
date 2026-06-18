
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
    respuesta_especifica = verificar_pregunta_especifica(mensaje, usuario, historial, datos)
    if respuesta_especifica:
        return respuesta_especifica
    
    # SI NO ES UNA PREGUNTA ESPECÍFICA: Intentar con Ollama primero
    if verificar_conexion_ollama():
        try:
            return preguntar_ollama(mensaje, datos, nombre_usuario, historial)
        except Exception as e:
            pass  # Fallback a la respuesta inteligente
    
    # ÚLTIMO RECURSO: Respuesta inteligente genérica
    return obtener_respuesta_inteligente(mensaje, usuario, historial, datos)

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
    
    # 1. OPERACIONES MATEMÁTICAS
    # Patrones para operaciones matemáticas
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
                    # Si es entero, mostrar sin decimales
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
    
    # 2. ALERTAS DE MATERIALES
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
    
    # 3. PREGUNTAS ESPECÍFICAS SOBRE EL SISTEMA
    # Vehículos
    if any(palabra in mensaje_lower for palabra in ["vehículo", "vehículos", "vehiculo", "vehiculos", "coche", "camión", "camion", "auto", "flota"]):
        if any(palabra in mensaje_lower for palabra in ["sin conductor", "sin asignar", "libres", "disponibles", "disponible"]):
            respuesta = f"Actualmente hay {datos['vehiculos_sin_conductor']} vehículos sin conductor y {datos['vehiculos_disponibles']} disponibles para usar."
        elif any(palabra in mensaje_lower for palabra in ["en ruta", "viajando", "en camino", "transitando"]):
            respuesta = f"Hay {datos['vehiculos_en_ruta']} vehículos en ruta y {datos['vehiculos_count']} en total en la flota."
        else:
            respuesta = f"En el sistema hay {datos['vehiculos_count']} vehículos: {datos['vehiculos_disponibles']} disponibles, {datos['vehiculos_en_ruta']} en ruta y {datos['vehiculos_sin_conductor']} sin conductor asignado."
        return f"{saludo} {respuesta}".strip()
    
    # Conductores
    if any(palabra in mensaje_lower for palabra in ["conductor", "conductores", "chofer", "choferes", "pilotos"]):
        respuesta = f"Actualmente hay {datos['conductor_count']} conductores registrados en el sistema."
        return f"{saludo} {respuesta}".strip()
    
    # Inventario
    if any(palabra in mensaje_lower for palabra in ["inventario", "material", "materiales", "stock", "almacén", "almacen", "productos"]):
        if any(palabra in mensaje_lower for palabra in ["bajo", "poco", "escasez", "faltante", "pocos"]):
            respuesta = f"Actualmente hay {datos['stock_bajo']} materiales con stock bajo. El total de tipos de materiales es {datos['total_materiales']} y hay {datos['total_stock']} unidades en total en stock."
        else:
            respuesta = f"El inventario tiene {datos['total_materiales']} tipos de materiales, con {datos['total_stock']} unidades en total y {datos['stock_bajo']} con stock bajo."
        return f"{saludo} {respuesta}".strip()
    
    # Pedidos
    if any(palabra in mensaje_lower for palabra in ["pedido", "pedidos", "orden", "órdenes", "ordenes", "solicitudes"]):
        respuesta = f"Tenemos {datos['pedidos_totales']} pedidos en total: {datos['pedidos_pendientes']} pendientes, {datos['pedidos_aprobados']} aprobados, {datos['pedidos_en_camino']} en camino, {datos['pedidos_entregados']} entregados y {datos['pedidos_cancelados']} cancelados."
        return f"{saludo} {respuesta}".strip()
    
    # Usuarios
    if any(palabra in mensaje_lower for palabra in ["usuario", "usuarios", "empleado", "empleados", "trabajador", "trabajadores", "personal"]):
        respuesta = f"Hay {datos['total_usuarios']} usuarios registrados: {datos['admin_count']} administradores, {datos['cliente_count']} clientes, {datos['conductor_count']} conductores y {datos['empleado_count']} empleados."
        return f"{saludo} {respuesta}".strip()
    
    # Ventas / Facturas
    if any(palabra in mensaje_lower for palabra in ["venta", "ventas", "factura", "facturas", "dinero", "ganancias", "ingresos"]):
        respuesta = f"Las ventas totales son ${datos['total_ventas']:,.2f}. Tenemos {datos['facturas_totales']} facturas (${datos['total_facturado']:,.2f} facturado) y {datos['pagos_totales']} pagos realizados por un total de ${datos['total_pagado']:,.2f}."
        return f"{saludo} {respuesta}".strip()
    
    # Compras
    if any(palabra in mensaje_lower for palabra in ["compra", "compras", "proveedor", "proveedores", "suministros"]):
        respuesta = f"Tenemos {datos['compras_totales']} compras registradas (${datos['total_compras']:,.2f} en total) y {datos['proveedores_count']} proveedores en el sistema."
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
        historial_texto = "\n\nHistorial de la conversación (últimos mensajes):\n"
        for msg in historial:
            if msg['sender'] == 'user':
                historial_texto += f"USUARIO: {msg['text']}\n"
            else:
                historial_texto += f"ASISTENTE: {msg['text']}\n"
    
    # Crear el prompt del sistema - MEJORADO MUCHO
    system_prompt = f"""Eres el ASISTENTE VIRTUAL DE CONSTRU-TRANS, un sistema de gestión para materiales de construcción.

Tu personalidad:
- Amigable, profesional y servicial
- Siempre respondes en español claro y conciso
- No pareces nuevo, pareces un asistente que ha estado aquí desde el principio
- Tienes conocimiento completo del sistema y de cómo funciona

Reglas ABSOLUTAS:
1. RESPONDE EN ESPAÑOL
2. SI EL USUARIO TE PREGUNTA POR DATOS DEL SISTEMA (pedidos, inventario, vehículos, conductores, facturas, etc.), usa el contexto proporcionado para responder con precisión
3. SI EL USUARIO TE PREGUNTA ALGO GENERAL (hora, qué es Constru-Trans, cómo estás, qué puedes hacer, etc.), responde de manera natural y fluida
4. SI EL USUARIO TE PREGUNTA POR CÁLCULOS, hazlos y responde con el resultado
5. SI EL USUARIO PREGUNTA POR ALERTAS O STOCK BAJO, usa el contexto
6. NO INVENTES DATOS, usa el contexto proporcionado
7. USA el HISTORIAL de la conversación para mantener la coherencia
8. SI EL USUARIO PREGUNTA ALGO QUE NO SABES pero está relacionado, sugiere preguntas específicas que sí puedes responder
9. SI EL USUARIO QUIERE CONTACTAR A ALGUIEN, explica que puedes ayudarle con la información del sistema pero que para contactar directamente debe usar las funcionalidades del sistema
10. SE COHERENTE con lo que ya dijiste anteriormente en la conversación

Datos del usuario:
- Nombre: {nombre_usuario if nombre_usuario else "No registrado"}

Contexto actual del sistema Constru-Trans:
{contexto_texto}
{historial_texto}

Recuerda:
- Eres el asistente de Constru-Trans, ya conoces todo el sistema
- No pareces nuevo, pareces experimentado
- Responde de manera fluida y natural"""

    # Construir la solicitud a Ollama
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
            timeout=90
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
    
    # Verificar si es la primera interacción
    es_primera_interaccion = len(historial) == 0
    
    # Convertir mensaje a minúsculas para mejor detección
    mensaje_lower = mensaje.lower()
    es_saludo = any(palabra in mensaje_lower for palabra in ["hola", "buenos días", "buenas tardes", "buenas noches", "qué tal", "cómo estás", "como estas", "buen día", "hey", "holi", "holis"])
    
    # Construir saludo
    saludo = ""
    if es_primera_interaccion or es_saludo:
        saludo = "¡Hola!"
        if usuario and usuario.is_authenticated:
            saludo = f"¡Hola {usuario.nombres}!"
    
    # --- SALUDOS Y BIENVENIDAS ---
    if es_saludo:
        respuestas_bienvenida = [
            "Soy tu asistente virtual de Constru-Trans. ¿En qué puedo ayudarte hoy? Puedo darte información sobre inventario, pedidos, vehículos, conductores y más!",
            "¡Qué gusto tenerte aquí! Soy tu asistente de Constru-Trans. ¿Qué necesitas?",
            "Estoy listo para ayudarte con todo lo relacionado al sistema. ¿En qué puedo colaborarte?",
            "¡Bienvenido! ¿Qué necesitas hoy? Puedo ayudarte con pedidos, inventario, facturas y mucho más.",
        ]
        return f"{saludo} {random.choice(respuestas_bienvenida)}".strip()
    
    # --- AYUDA ---
    if any(palabra in mensaje_lower for palabra in ["ayuda", "ayúdame", "ayudame", "qué puedes hacer", "que puedes hacer", "qué haces", "que haces", "qué sabes", "que sabes", "puedes hacer", "que puedo hacer"]):
        respuesta_ayuda = [
            "Estoy aquí para ayudarte con todo lo relacionado al sistema Constru-Trans. Puedes preguntarme sobre:\n- Estado de pedidos\n- Inventario y materiales\n- Vehículos y conductores\n- Ventas y facturas\n- Usuarios del sistema\n- Realizar cálculos matemáticos\n- Ver alertas de stock\n\n¿Qué necesitas?",
            "Puedo ayudarte con lo siguiente:\n- Información sobre pedidos y órdenes\n- Estado del inventario y materiales\n- Vehículos y conductores\n- Facturas, pagos y ventas\n- Cálculos matemáticos\n\n¿Qué te interesa?",
            "Soy tu asistente completo de Constru-Trans! Puedo darte información de todo el sistema, hacer cálculos, alertarte de stock bajo y mucho más. ¿Qué necesitas?",
        ]
        return f"{saludo} {random.choice(respuesta_ayuda)}".strip()
    
    # --- PREGUNTAS SOBRE CONSTRU-TRANS ---
    if any(palabra in mensaje_lower for palabra in ["qué es", "que es", "qué es constru-trans", "que es constru-trans", "de qué se trata", "de que se trata", "para qué sirve", "para que sirve"]):
        respuestas_que_es = [
            "Constru-Trans es un sistema de gestión integral para materiales de construcción. Te ayuda a administrar pedidos, inventario, vehículos, facturas y más.",
            "Somos un sistema completo de gestión de pedidos y transporte para materiales de construcción. ¡Estoy aquí para ayudarte con todo!",
            "Constru-Trans es la herramienta perfecta para administrar tu negocio de materiales de construcción: pedidos, inventario, facturación, todo en un solo lugar.",
        ]
        return f"{saludo} {random.choice(respuestas_que_es)}".strip()
    
    # --- PREGUNTAS SOBRE HORA ---
    if any(palabra in mensaje_lower for palabra in ["hora", "horas", "qué hora", "que hora", "tiempo", "fecha", "día", "dia"]):
        ahora = timezone.localtime()
        hora_actual = ahora.strftime("%H:%M")
        fecha_actual = ahora.strftime("%d/%m/%Y")
        dia_semana = ahora.strftime("%A")
        dias_semana_es = {
            "Monday": "lunes", "Tuesday": "martes", "Wednesday": "miércoles", 
            "Thursday": "jueves", "Friday": "viernes", "Saturday": "sábado", "Sunday": "domingo"
        }
        dia_semana_es = dias_semana_es.get(dia_semana, dia_semana)
        
        respuestas_hora = [
            f"Hoy es {dia_semana_es} {fecha_actual} y son las {hora_actual}.",
            f"Son las {hora_actual} del {fecha_actual} ({dia_semana_es}).",
            f"Ahora mismo son las {hora_actual}. Hoy es {dia_semana_es} {fecha_actual}.",
        ]
        return f"{saludo} {random.choice(respuestas_hora)}".strip()
    
    # --- PREGUNTAS SOBRE CÓMO ESTÁS ---
    if any(palabra in mensaje_lower for palabra in ["cómo estás", "como estas", "qué tal estás", "que tal estas", "cómo te va", "como te va", "cómo va", "como va"]):
        respuestas_estado = [
            "¡Muy bien, gracias! Listo para ayudarte. ¿Qué necesitas?",
            "Excelente, siempre listo para ayudarte en Constru-Trans. ¿En qué puedo colaborarte?",
            "¡Todo genial! ¿Qué necesitas hoy?",
            "Muy bien, listo para ayudarte con lo que necesites.",
        ]
        return f"{saludo} {random.choice(respuestas_estado)}".strip()
    
    # --- PREGUNTAS SOBRE CONTACTAR A ALGUIEN ---
    if any(palabra in mensaje_lower for palabra in ["contactar", "comunicar", "hablar con", "hablar a", "notificar", "enviar mensaje", "mandar mensaje", "llamar a", "contacto con", "persona", "soporte", "tecnico", "técnico", "alguien"]):
        respuestas_contacto = [
            "Claro, puedo ayudarte con la información del sistema. Si necesitas contactar directamente con alguien del equipo, te recomiendo usar las funcionalidades de notificación o comunicación que tiene el sistema Constru-Trans. ¿Qué información del sistema necesitas?",
            "Soy tu asistente del sistema Constru-Trans y puedo darte toda la información que necesites sobre pedidos, inventario, vehículos y más. Para contactar directamente con alguien, usa las opciones del sistema. ¿Qué te gustaría saber?",
            "Estoy aquí para ayudarte con datos del sistema. Si necesitas contactar a alguien específico, revisa las funcionalidades del sistema. ¿Qué información necesitas ahora?",
        ]
        return f"{saludo} {random.choice(respuestas_contacto)}".strip()
    
    # --- RESPUESTA POR DEFECTO (MEJORADA Y NATURAL) ---
    respuestas_por_defecto = [
        f"Claro, cuéntame qué necesitas. Actualmente tenemos {datos['pedidos_totales']} pedidos, {datos['total_materiales']} materiales y {datos['vehiculos_count']} vehículos. ¿Qué te interesa?",
        f"Por supuesto. Tenemos {datos['pedidos_pendientes']} pedidos pendientes y {datos['vehiculos_disponibles']} vehículos disponibles. ¿Qué necesitas saber?",
        "Estoy aquí para ayudarte. ¿Podrías ser un poco más específico? Puedo ayudarte con pedidos, inventario, vehículos, facturas, cálculos y más.",
        "Cuéntame, ¿qué necesitas hoy? Puedo darte información de todo el sistema Constru-Trans.",
        f"¿Qué te gustaría consultar? Hay {datos['total_usuarios']} usuarios, {datos['clientes_registrados']} clientes y {datos['proveedores_count']} proveedores. ¿Necesitas algo en específico?",
        "¿Qué necesitas? Estoy listo para ayudarte con lo que necesites del sistema.",
    ]
    
    return f"{saludo} {random.choice(respuestas_por_defecto)}".strip()

