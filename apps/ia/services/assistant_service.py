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
from .formatting_service import format_number_es
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


def normalizar_texto(texto):
    """Elimina acentos, puntuación y pasa a minúsculas"""
    texto = texto.lower()
    # Eliminar puntuación
    texto = re.sub(r'[^\w\s]', '', texto)
    # Eliminar acentos
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "à": "a", "è": "e", "ì": "i", "ò": "o", "ù": "u",
        "ä": "a", "ë": "e", "ï": "i", "ö": "o", "ü": "u"
    }
    for a, b in replacements.items():
        texto = texto.replace(a, b)
    return texto


def procesar_parte_pregunta(parte, datos):
    """Procesa una parte individual de la pregunta y devuelve la respuesta"""
    parte_normalizada = normalizar_texto(parte)
    respuestas = []

    # --- USUARIOS ---
    if any(k in parte_normalizada for k in ["usuario", "usuarios"]):
        if any(k in parte_normalizada for k in ["total", "hay", "cuantos", "cautnos", "qué hay", "hay cuantos", "hay cautnos"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('total_usuarios', 0))} usuarios registrados en total.")
        if any(k in parte_normalizada for k in ["activos", "activo"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('usuarios_activos', 0))} usuarios activos.")
        if any(k in parte_normalizada for k in ["admin", "administrador", "administradores"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('admin_count', 0))} administradores.")
        if any(k in parte_normalizada for k in ["cliente", "clientes"]) and not any(k in parte_normalizada for k in ["cliente registrado", "clientes registrados"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('cliente_count', 0))} usuarios con rol de cliente.")
        if any(k in parte_normalizada for k in ["conductor", "conductores"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('conductor_count', 0))} conductores.")
        if any(k in parte_normalizada for k in ["empleado", "empleados"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('empleado_count', 0))} empleados.")

    # --- CLIENTES ---
    if any(k in parte_normalizada for k in ["cliente", "clientes"]):
        if any(k in parte_normalizada for k in ["registrado", "registrados", "total", "hay", "cuantos", "cautnos", "cuántos"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('clientes_registrados', 0))} clientes registrados en el sistema.")

    # --- PROVEEDORES ---
    if any(k in parte_normalizada for k in ["proveedor", "proveedores", "provdores", "providores"]):
        if any(k in parte_normalizada for k in ["total", "hay", "cuantos", "cautnos", "cuántos", "que hay", "hay cuantos", "hay cautnos", "activos"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('proveedores_count', 0))} proveedores registrados.")

    # --- MATERIALES / STOCK ---
    if any(k in parte_normalizada for k in ["material", "materiales", "stock"]):
        if any(k in parte_normalizada for k in ["total", "hay", "cuantos", "cautnos", "cuántos", "que hay"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('total_materiales', 0))} tipos de materiales en el sistema.")
        if any(k in parte_normalizada for k in ["poco", "bajo", "alerta", "alertas", "acabando", "terminando", "sin stock"]):
            if datos.get('stock_bajo', 0) > 0:
                respuestas_alertas = [
                    f"¡Alerta! Hay {format_number_es(datos['stock_bajo'])} materiales con stock bajo. ¡Revisa el inventario!",
                    f"Aviso: {format_number_es(datos['stock_bajo'])} materiales están por acabarse. ¡No te olvides de reabastecer!",
                ]
                respuestas.append(random.choice(respuestas_alertas))
            else:
                respuestas_ok = [
                    "Todo bien en el inventario! No hay materiales con stock bajo.",
                    "Excelente, el inventario está en perfectas condiciones, sin alertas.",
                ]
                respuestas.append(random.choice(respuestas_ok))
        if any(k in parte_normalizada for k in ["total stock", "total de stock"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('total_stock', 0))} unidades en stock en total.")

    # --- VEHÍCULOS ---
    if any(k in parte_normalizada for k in ["vehiculo", "vehiculos", "vehículo", "vehículos", "auto", "autos", "carro", "carros", "camion", "camiones"]):
        if any(k in parte_normalizada for k in ["total", "hay", "cuantos", "cautnos", "cuántos"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('vehiculos_count', 0))} vehículos registrados en total.")
        if any(k in parte_normalizada for k in ["disponible", "disponibles", "libre", "libres"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('vehiculos_disponibles', 0))} vehículos disponibles y {format_number_es(datos.get('vehiculos_en_ruta', 0))} en ruta. En total hay {format_number_es(datos.get('vehiculos_count', 0))} vehículos en el sistema.")
        if any(k in parte_normalizada for k in ["en ruta", "ruta", "ocupados"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('vehiculos_en_ruta', 0))} vehículos en ruta y {format_number_es(datos.get('vehiculos_disponibles', 0))} disponibles.")

    # --- PEDIDOS ---
    if any(k in parte_normalizada for k in ["pedido", "pedidos"]):
        if any(k in parte_normalizada for k in ["total", "hay", "cuantos", "cautnos", "cuántos"]):
            respuestas.append(f"Resumen de pedidos: {format_number_es(datos.get('pedidos_totales', 0))} totales, {format_number_es(datos.get('pedidos_pendientes', 0))} pendientes, {format_number_es(datos.get('pedidos_aprobados', 0))} aprobados, {format_number_es(datos.get('pedidos_en_camino', 0))} en camino, {format_number_es(datos.get('pedidos_entregados', 0))} entregados y {format_number_es(datos.get('pedidos_cancelados', 0))} cancelados. El total de ventas es de {format_number_es(datos.get('total_ventas', 0))}.")
        if any(k in parte_normalizada for k in ["pendiente", "pendientes"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('pedidos_pendientes', 0))} pedidos pendientes.")
        if any(k in parte_normalizada for k in ["aprobado", "aprobados"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('pedidos_aprobados', 0))} pedidos aprobados.")
        if any(k in parte_normalizada for k in ["en camino", "camino"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('pedidos_en_camino', 0))} pedidos en camino.")
        if any(k in parte_normalizada for k in ["entregado", "entregados"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('pedidos_entregados', 0))} pedidos entregados.")
        if any(k in parte_normalizada for k in ["cancelado", "cancelados"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('pedidos_cancelados', 0))} pedidos cancelados.")
        if any(k in parte_normalizada for k in ["ventas", "total vendido", "ventas totales"]):
            respuestas.append(f"El total de ventas es de {format_number_es(datos.get('total_ventas', 0))}.")

    # --- COMPRAS ---
    if any(k in parte_normalizada for k in ["compra", "compras"]):
        if any(k in parte_normalizada for k in ["total", "hay", "cuantos", "cautnos", "cuántos"]):
            respuestas.append(f"Resumen de compras: {format_number_es(datos.get('compras_totales', 0))} totales, {format_number_es(datos.get('compras_pendientes', 0))} pendientes y {format_number_es(datos.get('compras_recibidas', 0))} recibidas. El total de compras es de {format_number_es(datos.get('total_compras', 0))}.")
        if any(k in parte_normalizada for k in ["pendiente", "pendientes"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('compras_pendientes', 0))} compras pendientes.")
        if any(k in parte_normalizada for k in ["recibida", "recibidas"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('compras_recibidas', 0))} compras recibidas.")
        if any(k in parte_normalizada for k in ["total compras", "total de compras"]):
            respuestas.append(f"El total de compras es de {format_number_es(datos.get('total_compras', 0))}.")

    # --- FACTURAS ---
    if any(k in parte_normalizada for k in ["factura", "facturas"]):
        if any(k in parte_normalizada for k in ["total", "hay", "cuantos", "cautnos", "cuántos"]):
            respuestas.append(f"Resumen de facturas: {format_number_es(datos.get('facturas_totales', 0))} totales, {format_number_es(datos.get('facturas_pendientes', 0))} pendientes y {format_number_es(datos.get('facturas_pagadas', 0))} pagadas. El total facturado es de {format_number_es(datos.get('total_facturado', 0))}.")
        if any(k in parte_normalizada for k in ["pendiente", "pendientes"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('facturas_pendientes', 0))} facturas pendientes.")
        if any(k in parte_normalizada for k in ["pagada", "pagadas"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('facturas_pagadas', 0))} facturas pagadas.")
        if any(k in parte_normalizada for k in ["total facturado", "facturado total"]):
            respuestas.append(f"El total facturado es de {format_number_es(datos.get('total_facturado', 0))}.")

    # --- PAGOS ---
    if any(k in parte_normalizada for k in ["pago", "pagos"]):
        if any(k in parte_normalizada for k in ["total", "hay", "cuantos", "cautnos", "cuántos"]):
            respuestas.append(f"Actualmente hay {format_number_es(datos.get('pagos_totales', 0))} pagos registrados, con un total pagado de {format_number_es(datos.get('total_pagado', 0))}.")
        if any(k in parte_normalizada for k in ["total pagado", "pagado total"]):
            respuestas.append(f"El total pagado es de {format_number_es(datos.get('total_pagado', 0))}.")

    return respuestas


def verificar_pregunta_especifica(mensaje, usuario, historial, datos):
    """Verifica si la pregunta es específica y devuelve la respuesta (incluye múltiples partes)"""
    mensaje_lower = mensaje.lower()
    mensaje_normalizado = normalizar_texto(mensaje)
    es_primera_interaccion = len(historial) == 0
    respuestas = []

    # Construir saludo
    saludo = ""
    es_saludo = any(palabra in mensaje_normalizado for palabra in ["hola", "buenos dias", "buenas tardes", "buenas noches", "que tal", "como estas", "buen dia", "hey", "holi", "holis"])
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
                    respuestas.append(f"{resultado}")
    except Exception:
        logger.exception("Error en verificar_pregunta_especifica matemáticas")

    # 2. Preprocesar: separar "y" que está pegado a palabras (ej: "conductory" → "conductor y")
    mensaje_procesado = re.sub(r'(\w)y(\w)', r'\1 y \2', mensaje_normalizado)
    mensaje_procesado = re.sub(r'(\w)y(\s)', r'\1 y ', mensaje_procesado)
    mensaje_procesado = re.sub(r'(\s)y(\w)', r' y \2', mensaje_procesado)

    # 3. Separar la pregunta en partes usando "y", "y que", "que", "qué"
    patrones_separadores = [
        r'\s+y\s+',       # " y "
        r'\s+y que\s+',   # " y que "
        r'\s+y qué\s+',   # " y qué "
        r'\s+que\s+',     # " que "
        r'\s+qué\s+',     # " qué "
        r'\s+y\s+que\s+', # " y que "
        r'\s+y\s+qué\s+', # " y qué "
    ]
    partes = [mensaje_procesado]
    for patron in patrones_separadores:
        nuevas_partes = []
        for parte in partes:
            nuevas_partes.extend(re.split(patron, parte))
        partes = nuevas_partes
    # Limpiar partes vacías o muy cortas
    partes = [p.strip() for p in partes if p.strip() and len(p.strip()) > 2]

    # 3. Procesar cada parte
    for parte in partes:
        respuestas.extend(procesar_parte_pregunta(parte, datos))

    # 4. Si no se procesaron partes, intentar con la pregunta entera
    if not respuestas:
        respuestas.extend(procesar_parte_pregunta(mensaje_normalizado, datos))

    # 5. Resumen general si aún no hay respuestas
    if not respuestas and any(k in mensaje_normalizado for k in ["resumen", "sistema", "que hay", "qué hay", "que tiene", "qué tiene"]):
        respuestas.append(f"""Resumen del sistema Constru-Trans:
- Usuarios: {format_number_es(datos.get('total_usuarios', 0))} totales, {format_number_es(datos.get('usuarios_activos', 0))} activos
- Clientes: {format_number_es(datos.get('clientes_registrados', 0))} registrados
- Proveedores: {format_number_es(datos.get('proveedores_count', 0))}
- Materiales: {format_number_es(datos.get('total_materiales', 0))} tipos
- Vehículos: {format_number_es(datos.get('vehiculos_count', 0))} total
- Pedidos: {format_number_es(datos.get('pedidos_totales', 0))} totales""")

    if respuestas:
        # Eliminar duplicados (mantener orden)
        respuestas_unicas = []
        visto = set()
        for r in respuestas:
            if r not in visto:
                visto.add(r)
                respuestas_unicas.append(r)
        if saludo:
            return f"{saludo}\n" + "\n".join(respuestas_unicas)
        return "\n".join(respuestas_unicas)

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
            "Soy tu asistente virtual de Constru-Trans. ¿En qué puedo ayudarte hoy? Puedo darte información sobre inventario, pedidos, vehículos, facturas, compras y más!",
            "¡Qué gusto tenerte aquí! Soy tu asistente de Constru-Trans. ¿Qué necesitas?",
        ]
        return f"{saludo} {random.choice(respuestas_bienvenida)}".strip()

    if any(palabra in mensaje_lower for palabra in ["ayuda", "ayúdame", "ayudame", "que puedes hacer", "qué puedes hacer", "que haces", "qué haces", "que sabes", "qué sabes", "puedes hacer", "que puedo hacer"]):
        respuesta_ayuda = [
            """Estoy aquí para ayudarte con:
- Hora y fecha actual (también en otros países)
- Cálculos matemáticos
- Información del sistema:
  • Usuarios, clientes y proveedores
  • Materiales y stock
  • Vehículos
  • Pedidos
  • Compras
  • Facturas y pagos
- Preguntas generales o conversacionales""",
        ]
        return f"{saludo} {random.choice(respuesta_ayuda)}".strip()

    respuestas_por_defecto = [
        "No he podido resolver esa consulta con el motor principal en este momento. Si quieres, reformula la pregunta o prueba preguntarme algo específico del sistema como '¿cuántos pedidos hay?'",
        "Estoy aquí para ayudarte. Prueba preguntarme sobre la hora, el inventario, los pedidos, los proveedores o los vehículos!",
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
