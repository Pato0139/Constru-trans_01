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
from .semantic_memory_service import buscar_memoria, guardar_interaccion
from .llm_service import preguntar_llm
from .time_service import responder_hora
from apps.ia.models import UserFeedback, AIPromptTemplate, ConversationMessage

logger = logging.getLogger(__name__)


def expandir_mensaje_contextual(mensaje: str, historial: list) -> str:
    m = (mensaje or "").strip().lower()

    if not historial:
        return mensaje

    if m.startswith("y en "):
        ultimos_usuario = [
            h.get("content") or h.get("text") or ""
            for h in reversed(historial)
            if (h.get("role") == "user" or h.get("sender") == "user")
        ]
        ultimo = ultimos_usuario[0].lower() if ultimos_usuario else ""

        if any(k in ultimo for k in ["hora", "horas", "día", "dia", "noche", "qué hora", "que hora"]):
            lugar = mensaje.strip()[4:].strip()
            return f"¿Qué hora es en {lugar} y si es de día o de noche?"

    return mensaje


def verificar_pregunta_especifica(mensaje, usuario, historial, datos):
    """Verifica si la pregunta es específica y devuelve la respuesta"""
    mensaje_lower = mensaje.lower()
    es_primera_interaccion = len(historial) == 0
    mensaje_sin_puntuacion = re.sub(r'[^\w\s]', '', mensaje_lower).strip()

    # Construir saludo
    saludo = ""
    es_saludo = any(palabra in mensaje_lower for palabra in ["hola", "buenos días", "buenas tardes", "buenas noches", "qué tal", "cómo estás", "como estas", "buen día", "hey", "holi", "holis"])
    if es_primera_interaccion or es_saludo:
        saludo = "¡Hola!"
        if usuario and usuario.is_authenticated:
            saludo = f"¡Hola {usuario.nombres}!"

    # 1. OPERACIONES MATEMÁTICAS
    try:
        allowed_chars = re.compile(r'[\d\.\(\)\+\-\*/\^\s]|más|menos|por|entre|ra[íi]z|sqrt|sen|sin|cos|tan|log|ln|exp|pi|e|fact|factorial|abs|round', re.IGNORECASE)
        extracted_parts = allowed_chars.findall(mensaje_lower)
        if extracted_parts:
            extracted_expr = "".join(extracted_parts).strip()
            if extracted_expr and len(extracted_expr) >= 3:
                resultado = evaluar_expresion_matematica(extracted_expr)
                if resultado is not None:
                    return f"{saludo} {resultado}"
    except Exception:
        logger.exception("Error en verificar_pregunta_especifica matemáticas")

    # 2. ALERTAS DE MATERIALES
    if ("alerta" in mensaje_lower and "material" in mensaje_lower) or "stock bajo" in mensaje_lower or "qué materiales" in mensaje_lower:
        if datos.get('stock_bajo', 0) > 0:
            respuestas_alertas = [
                f"¡Alerta! Hay {datos['stock_bajo']} materiales con stock bajo. ¡Revisa el inventario!",
                f"Aviso: {datos['stock_bajo']} materiales están por acabarse. ¡No te olvides de reabastecer!",
            ]
            return f"{saludo} {random.choice(respuestas_alertas)}"
        else:
            respuestas_ok = [
                "Todo bien en el inventario! No hay materiales con stock bajo.",
                "Excelente, el inventario está en perfectas condiciones, sin alertas.",
            ]
            return f"{saludo} {random.choice(respuestas_ok)}"

    # 3. VEHICULOS
    if "vehículos" in mensaje_lower or "vehiculos" in mensaje_lower or "autos" in mensaje_lower or "camiones" in mensaje_lower:
        return f"{saludo} Actualmente hay {datos.get('vehiculos_disponibles', 0)} vehículos disponibles y {datos.get('vehiculos_en_ruta', 0)} en ruta. En total hay {datos.get('vehiculos_count', 0)} vehículos en el sistema."

    # 4. PEDIDOS
    if "pedidos" in mensaje_lower or "pedido" in mensaje_lower:
        return f"{saludo} Resumen de pedidos: {datos.get('pedidos_totales', 0)} totales, {datos.get('pedidos_pendientes', 0)} pendientes, {datos.get('pedidos_aprobados', 0)} aprobados, {datos.get('pedidos_en_camino', 0)} en camino, {datos.get('pedidos_entregados', 0)} entregados y {datos.get('pedidos_cancelados', 0)} cancelados."

    # 5. DATOS GENERALES DEL SISTEMA
    if "resumen" in mensaje_lower or "sistema" in mensaje_lower or "qué hay" in mensaje_lower or "cuántos" in mensaje_lower:
        return f"{saludo} Resumen del sistema Constru-Trans: {datos.get('total_usuarios', 0)} usuarios, {datos.get('clientes_registrados', 0)} clientes, {datos.get('proveedores_count', 0)} proveedores, {datos.get('total_materiales', 0)} tipos de materiales, {datos.get('vehiculos_count', 0)} vehículos y {datos.get('pedidos_totales', 0)} pedidos."

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
            "Estoy aquí para ayudarte con:\n- Hora y fecha actual\n- Cálculos matemáticos\n- Información de inventario (usa 'alerta de stock' o 'stock bajo')\n- Estado de vehículos (usa 'vehículos disponibles')\n- Resumen de pedidos (usa 'pedidos pendientes')\n- Resumen del sistema (usa 'resumen del sistema')",
        ]
        return f"{saludo} {random.choice(respuesta_ayuda)}".strip()

    respuestas_por_defecto = [
        "No he podido resolver esa consulta con el motor principal en este momento. Si quieres, reformula la pregunta o lo intento con una respuesta general.",
        "Estoy aquí para ayudarte. Prueba preguntarme sobre la hora, el inventario o los pedidos pendientes.",
    ]

    return f"{saludo} {random.choice(respuestas_por_defecto)}".strip()


def preguntar_ia(mensaje, usuario=None, historial=None, session_id=None):
    start_time = time.time()

    conversation = get_conversation(usuario, session_id)
    add_message_to_conversation(conversation, "user", mensaje)

    # Obtener historial real de la BD
    historial_db = [
        {"role": m.role, "content": m.content}
        for m in conversation.messages.order_by("timestamp")[:20]
    ]

    # Expandir mensaje contextual
    mensaje = expandir_mensaje_contextual(mensaje, historial_db)

    datos = obtener_contexto_datos()
    nombre_usuario = ""
    rol_usuario = None
    user_id = None
    if usuario and usuario.is_authenticated:
        nombre_usuario = f"{usuario.nombres} {usuario.apellidos}".strip()
        rol_usuario = getattr(usuario, "rol", None)
        user_id = str(usuario.id)

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

        # Primero probar time_service
        respuesta_hora = responder_hora(mensaje)
        if respuesta_hora:
            bot_message = add_message_to_conversation(
                conversation,
                "assistant",
                respuesta_hora,
                prompt_used="Time-Service",
                model_used="Rule-Based",
                response_time=time.time() - start_time,
            )
            return respuesta_hora, bot_message.id if bot_message else None

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

        # Buscar memoria semántica
        memorias = buscar_memoria(mensaje, n_results=3)
        memoria_txt = "\n".join(memorias) if memorias else "Sin memoria relevante."
        mensaje_enriquecido = f"Memoria relevante:\n{memoria_txt}\n\nPregunta del usuario:\n{mensaje}"

        # Intentar LLM directamente
        respuesta_llm = preguntar_llm(mensaje_enriquecido, datos, nombre_usuario, historial_db)
        if respuesta_llm:
            bot_message = add_message_to_conversation(
                conversation,
                "assistant",
                respuesta_llm,
                prompt_used="OpenAI-Compatible Chat",
                model_used="generic-local-llm",
                response_time=time.time() - start_time,
            )

            # Guardar interacción en memoria semántica
            guardar_interaccion(
                doc_id=f"conv-{conversation.id}-{int(time.time())}",
                texto=f"Usuario: {mensaje}\nAsistente: {respuesta_llm}",
                metadata={"conversation_id": conversation.id}
            )

            return respuesta_llm, bot_message.id if bot_message else None

        # Fallback
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
