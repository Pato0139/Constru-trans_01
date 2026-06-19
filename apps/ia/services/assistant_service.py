import logging
import random
import time
import re
from django.utils import timezone
from datetime import datetime

from .context_service import obtener_contexto_datos
from .conversation_service import get_conversation, add_message_to_conversation
from .kb_service import check_knowledge_base, update_knowledge_base
from .math_service import evaluar_expresion_matematica
from .ollama_service import preguntar_ollama, verificar_conexion_ollama
from apps.ia.models import UserFeedback, AIPromptTemplate, ConversationMessage

logger = logging.getLogger(__name__)


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

    # 2. OPERACIONES MATEMÁTICAS - SUPER MEJORADA!
    try:
        # Lista de frases que indican una pregunta de matemáticas
        math_indicators = [
            "cuánto es", "cuanto es", "calcula", "resuelve", "qué es", "cuál es",
            "dime el resultado de", "resultado de", "calcular", "resolver",
            "qué es la raíz", "cuánto es la raíz", "calcula la raíz"
        ]
        
        # Extraer la parte matemática del mensaje
        expr_to_test = None
        
        # Primero, revisar si hay frases de math_indicators
        for indicator in math_indicators:
            if indicator in mensaje_lower:
                # Tomar todo lo que viene DESPUÉS del indicador
                idx = mensaje_lower.find(indicator)
                expr_to_test = mensaje_lower[idx + len(indicator):].strip()
                if expr_to_test:
                    break
        
        # Si no encontramos, probamos con todo el mensaje
        if not expr_to_test:
            expr_to_test = mensaje
        
        # Eliminar artículos y palabras de relleno del principio
        filler_words = ["la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "de", "del"]
        expr_parts = expr_to_test.split()
        while len(expr_parts) > 0 and expr_parts[0].lower() in filler_words:
            expr_parts.pop(0)
        expr_to_test = " ".join(expr_parts)
            
        # Intentar evaluar la expresión
        resultado = evaluar_expresion_matematica(expr_to_test)
        if resultado is not None:
            return f"{saludo} {resultado}".strip()
        
        # Si no funcionó, intentar extraer sólo números, operadores y funciones matemáticas
        # Filtramos el mensaje para dejar sólo caracteres matemáticos
        allowed_chars = re.compile(r'[\d\.\(\)\+\-\*/\^\s]|más|menos|por|entre|ra[íi]z|sqrt|sen|sin|cos|tan|log|ln|exp|pi|e|fact|factorial|abs|round', re.IGNORECASE)
        extracted_parts = allowed_chars.findall(mensaje_lower)
        if extracted_parts:
            extracted_expr = "".join(extracted_parts).strip()
            if extracted_expr:
                resultado = evaluar_expresion_matematica(extracted_expr)
                if resultado is not None:
                    return f"{saludo} {resultado}".strip()
    
    except Exception:
        logger.exception("Error en verificar_pregunta_especifica matemáticas")

    # 3. ALERTAS DE MATERIALES
    palabras_clave_alertas = [
        "alerta", "alertas", "poco material", "material bajo", "stock bajo",
        "qué materiales", "que materiales", "materiales con poco",
        "acabarse", "terminándose", "terminando", "sin stock", "sin materiales",
        "hay poco", "falta", "faltan", "aviso", "notificación"
    ]
    if any(palabra in mensaje_lower for palabra in palabras_clave_alertas):
        if datos.get('stock_bajo', 0) > 0:
            respuestas_alertas = [
                f"¡Alerta! Hay {datos['stock_bajo']} materiales con stock bajo. ¡Revisa el inventario!",
                f"Aviso: {datos['stock_bajo']} materiales están por acabarse. ¡No te olvides de reabastecer!",
            ]
            return f"{saludo} {random.choice(respuestas_alertas)}".strip()
        else:
            respuestas_ok = [
                "Todo bien en el inventario! No hay materiales con stock bajo.",
                "Excelente, el inventario está en perfectas condiciones, sin alertas.",
            ]
            return f"{saludo} {random.choice(respuestas_ok)}".strip()

    # 4. VEHICULOS DISPONIBLES
    palabras_clave_vehiculos = [
        "vehículos disponibles", "vehiculos disponibles", "qué vehículos están disponibles", "que vehiculos estan disponibles",
        "autos disponibles", "camiones disponibles", "vehiculos libres", "vehículos libres"
    ]
    if any(palabra in mensaje_lower for palabra in palabras_clave_vehiculos):
        return f"{saludo} Actualmente hay {datos.get('vehiculos_disponibles', 0)} vehículos disponibles y {datos.get('vehiculos_en_ruta', 0)} en ruta. En total hay {datos.get('vehiculos_count', 0)} vehículos en el sistema.".strip()

    # 5. PEDIDOS
    palabras_clave_pedidos = [
        "pedidos pendientes", "cuántos pedidos hay", "cuantos pedidos hay", "qué pedidos hay", "que pedidos hay",
        "estado de pedidos", "pedidos totales"
    ]
    if any(palabra in mensaje_lower for palabra in palabras_clave_pedidos):
        return f"{saludo} Resumen de pedidos: {datos.get('pedidos_totales', 0)} totales, {datos.get('pedidos_pendientes', 0)} pendientes, {datos.get('pedidos_aprobados', 0)} aprobados, {datos.get('pedidos_en_camino', 0)} en camino, {datos.get('pedidos_entregados', 0)} entregados y {datos.get('pedidos_cancelados', 0)} cancelados.".strip()

    # 6. DATOS GENERALES DEL SISTEMA
    palabras_clave_sistema = [
        "dime sobre el sistema", "resumen del sistema", "qué hay en el sistema", "que hay en el sistema",
        "cuántos usuarios hay", "cuantos usuarios hay", "cuántos clientes hay", "cuantos clientes hay",
        "cuántos proveedores hay", "cuantos proveedores hay"
    ]
    if any(palabra in mensaje_lower for palabra in palabras_clave_sistema):
        return f"{saludo} Resumen del sistema Constru-Trans: {datos.get('total_usuarios', 0)} usuarios, {datos.get('clientes_registrados', 0)} clientes, {datos.get('proveedores_count', 0)} proveedores, {datos.get('total_materiales', 0)} tipos de materiales, {datos.get('vehiculos_count', 0)} vehículos y {datos.get('pedidos_totales', 0)} pedidos.".strip()

    return None


def obtener_respuesta_inteligente(mensaje, usuario=None, historial=None, datos=None):
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
            "Soy tu asistente virtual de Constru-Trans. ¿En qué puedo ayudarte hoy? Puedo darte información sobre inventario, pedidos, vehículos y más!",
            "¡Qué gusto tenerte aquí! Soy tu asistente de Constru-Trans. ¿Qué necesitas?",
        ]
        return f"{saludo} {random.choice(respuestas_bienvenida)}".strip()

    if any(palabra in mensaje_lower for palabra in ["ayuda", "ayúdame", "ayudame", "qué puedes hacer", "que puedes hacer", "qué haces", "que haces", "qué sabes", "que sabes", "puedes hacer", "que puedo hacer"]):
        respuesta_ayuda = [
            "Estoy aquí para ayudarte con TODO lo que necesites: desde información del sistema Constru-Trans hasta cálculos matemáticos.",
        ]
        return f"{saludo} {random.choice(respuesta_ayuda)}".strip()

    respuestas_por_defecto = [
        "Estoy aquí para ayudarte. ¿En qué puedo asistirte hoy?",
        "Claro, cuéntame más sobre lo que necesitas.",
    ]

    return f"{saludo} {random.choice(respuestas_por_defecto)}".strip()


def preguntar_ia(mensaje, usuario=None, historial=None, session_id=None):
    historial = historial or []
    start_time = time.time()

    conversation = get_conversation(usuario, session_id)
    add_message_to_conversation(conversation, "user", mensaje)

    datos = obtener_contexto_datos()
    nombre_usuario = ""
    if usuario and usuario.is_authenticated:
        nombre_usuario = f"{usuario.nombres} {usuario.apellidos}".strip()

    try:
        kb_entry = check_knowledge_base(mensaje)
        if kb_entry:
            respuesta = kb_entry.best_response
            bot_message = add_message_to_conversation(
                conversation,
                "assistant",
                respuesta,
                prompt_used="Knowledge Base",
                model_used="Knowledge Base",
                response_time=time.time() - start_time,
            )
            return respuesta, bot_message.id if bot_message else None

        respuesta_especifica = verificar_pregunta_especifica(mensaje, usuario, historial, datos)
        if respuesta_especifica:
            bot_message = add_message_to_conversation(
                conversation,
                "assistant",
                respuesta_especifica,
                prompt_used="Rule-Based",
                model_used="Rule-Based",
                response_time=time.time() - start_time,
            )
            return respuesta_especifica, bot_message.id if bot_message else None

        if verificar_conexion_ollama():
            respuesta_ollama = preguntar_ollama(mensaje, datos, nombre_usuario, historial)
            if respuesta_ollama:
                bot_message = add_message_to_conversation(
                    conversation,
                    "assistant",
                    respuesta_ollama,
                    prompt_used="Ollama Chat",
                    model_used="llama3.2",
                    response_time=time.time() - start_time,
                )
                return respuesta_ollama, bot_message.id if bot_message else None

        respuesta_default = obtener_respuesta_inteligente(mensaje, usuario, historial, datos)
        bot_message = add_message_to_conversation(
            conversation,
            "assistant",
            respuesta_default,
            prompt_used="Default",
            model_used="Default",
            response_time=time.time() - start_time,
        )
        return respuesta_default, bot_message.id if bot_message else None
    except Exception:
        logger.exception("Fallo general en preguntar_ia")
        respuesta_error = "Ha ocurrido un problema procesando tu solicitud. Inténtalo de nuevo."
        bot_message = add_message_to_conversation(
            conversation,
            "assistant",
            respuesta_error,
            prompt_used="Error Fallback",
            model_used="Default",
            response_time=time.time() - start_time,
        )
        return respuesta_error, bot_message.id if bot_message else None


def save_feedback(message_id, feedback, comment=None, user=None):
    """Guarda el feedback y actualiza la base de conocimiento"""
    try:
        message = ConversationMessage.objects.get(id=message_id)

        fb = UserFeedback.objects.create(
            message=message,
            user=user,
            feedback=feedback,
            comment=comment
        )

        user_message = (
            message.conversation.messages
            .filter(role="user", timestamp__lte=message.timestamp)
            .order_by("-timestamp")
            .first()
        )
        if user_message:
            update_knowledge_base(user_message.content, message.content, feedback)

        for template in AIPromptTemplate.objects.filter(is_active=True):
            template.update_success_rate()

        return True
    except Exception:
        logger.exception("Error en save_feedback")
        return False


def auto_optimize_prompts():
    """Auto-optimiza prompts basado en feedback"""
    try:
        low_performing = AIPromptTemplate.objects.filter(
            is_active=True,
            success_rate__lt=50,
            usage_count__gt=5
        )

        for template in low_performing:
            template.is_active = False
            template.save()

        return True
    except Exception:
        logger.exception("Error en auto_optimize_prompts")
        return False
