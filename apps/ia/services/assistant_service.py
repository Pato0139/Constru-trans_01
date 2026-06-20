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


def has_keywords(check_strings, keywords):
    """Check if any keyword exists in any of the check_strings, with normalization"""
    # Normalize all keywords first
    normalized_keywords = []
    for k in keywords:
        normalized_keywords.append(k)
        normalized_keywords.append(normalizar_texto(k))
    normalized_keywords = list(set(normalized_keywords))  # Remove duplicates
    
    # Check both original and normalized check strings
    for s in check_strings:
        normalized_s = normalizar_texto(s)
        for k in normalized_keywords:
            if k in s or k in normalized_s:
                return True
    return False

def procesar_parte_pregunta(parte, datos, secciones_vistas=None):
    """Procesa una parte individual de la pregunta y devuelve la respuesta"""
    if secciones_vistas is None:
        secciones_vistas = set()
        
    parte_normalizada = normalizar_texto(parte)
    parte_lower = parte.lower()
    # Also create a combined check list that includes both normalized and original lower
    check_strings = [parte_normalizada, parte_lower]
    respuestas = []

    # --- 0. OPERACIONES MATEMÁTICAS PRIMERO (para esta parte) ---
    try:
        tiene_numeros = bool(re.search(r'\d', parte))
        tiene_palabras_matematicas = has_keywords(check_strings, ["cuanto es", "cuánto es", "calcular", "calcula", "resultado de", "sumar", "restar", "multiplicar", "dividir"])
        
        if tiene_numeros or tiene_palabras_matematicas:
            allowed_chars = re.compile(r'[\d\.\(\)\+\-\*/\^\s]|más|menos|por|entre|ra[íi]z|sqrt|sen|sin|cos|tan|log|ln|exp|pi|e|fact|factorial|abs|round', re.IGNORECASE)
            extracted_parts = allowed_chars.findall(parte_lower)
            if extracted_parts:
                extracted_expr = "".join(extracted_parts).strip()
                tiene_digito = bool(re.search(r'\d', extracted_expr))
                tiene_operacion = bool(re.search(r'[\+\-\*/\^]|más|menos|por|entre|ra[íi]z|sqrt|sen|sin|cos|tan|log|ln|exp|pi|fact|factorial|abs|round', extracted_expr, re.IGNORECASE))
                if tiene_digito or tiene_operacion:
                    if extracted_expr and len(extracted_expr) >= 3:
                        resultado = evaluar_expresion_matematica(extracted_expr)
                        if resultado is not None:
                            respuestas.append(f"{resultado}")
    except Exception:
        logger.exception("Error en procesar_parte_pregunta matemáticas")

    # --- USUARIOS ---
    if has_keywords(check_strings, ["usuario", "usuarios", "admin", "administrador", "administradores", "adminds", "conductor", "conductores", "cliente", "clientes", "empleado", "empleados"]) and "ESTADO DE USUARIOS" not in secciones_vistas:
        lineas = ["ESTADO DE USUARIOS"]
        
        hay_vehiculos = has_keywords(check_strings, ["vehiculo", "vehiculos", "vehículo", "vehículos", "auto", "autos", "carro", "carros", "camion", "camiones", "asociado", "asignado", "cada conductor"])
        if not hay_vehiculos or has_keywords(check_strings, ["usuario", "usuarios", "total", "hay", "cuantos", "cautnos", "qué hay", "hay cuantos", "hay cautnos", "activos", "activo", "admin", "administrador", "administradores", "cliente", "clientes", "empleado", "empleados"]):
            if has_keywords(check_strings, ["total", "hay", "cuantos", "cautnos", "qué hay", "hay cuantos", "hay cautnos"]):
                lineas.append(f"- Usuarios totales: {format_number_es(datos.get('total_usuarios', 0))}")
                lineas.append(f"- Usuarios activos: {format_number_es(datos.get('usuarios_activos', 0))}")
            if has_keywords(check_strings, ["admin", "administrador", "administradores"]):
                lineas.append(f"- Administradores: {format_number_es(datos.get('admin_count', 0))}")
            if has_keywords(check_strings, ["cliente", "clientes"]) and not has_keywords(check_strings, ["cliente registrado", "clientes registrados"]):
                lineas.append(f"- Clientes: {format_number_es(datos.get('cliente_count', 0))}")
            if has_keywords(check_strings, ["empleado", "empleados"]):
                lineas.append(f"- Empleados: {format_number_es(datos.get('empleado_count', 0))}")
            # Solo agregamos conductores si NO hay nada de vehículos en la misma parte de pregunta
            if has_keywords(check_strings, ["conductor", "conductores"]) and not hay_vehiculos:
                lineas.append(f"- Conductores: {format_number_es(datos.get('conductor_count', 0))}")
        
        if len(lineas) > 1:
            secciones_vistas.add("ESTADO DE USUARIOS")
            respuestas.append("\n".join(lineas))

    # --- CLIENTES ---
    if has_keywords(check_strings, ["cliente", "clientes"]) and "CLIENTES" not in secciones_vistas:
        if has_keywords(check_strings, ["registrado", "registrados", "total", "hay", "cuantos", "cautnos", "cuántos"]):
            lineas = ["CLIENTES"]
            lineas.append(f"- Clientes registrados: {format_number_es(datos.get('clientes_registrados', 0))}")
            secciones_vistas.add("CLIENTES")
            respuestas.append("\n".join(lineas))
    
    # --- TOP CLIENTE ---
    if has_keywords(check_strings, ["cliente", "clientes", "más pedidos", "mas pedidos", "que mas pedidos", "que más pedidos", "top cliente", "cliente top"]) and "TOP CLIENTE" not in secciones_vistas:
        top_cliente = datos.get('top_cliente')
        if top_cliente:
            lineas = ["CLIENTE CON MÁS PEDIDOS"]
            lineas.append(f"- {top_cliente['nombre']} con {format_number_es(top_cliente['num_pedidos'])} pedidos")
            secciones_vistas.add("TOP CLIENTE")
            respuestas.append("\n".join(lineas))
        else:
            respuestas.append("Aún no hay pedidos registrados para los clientes.")

    # --- PROVEEDORES ---
    if has_keywords(check_strings, ["proveedor", "proveedores", "provdores", "providores", "provedor", "provedores"]) and "PROVEEDORES" not in secciones_vistas:
        if has_keywords(check_strings, ["total", "hay", "cuantos", "cautnos", "cuántos", "que hay", "hay cuantos", "hay cautnos", "activos"]):
            lineas = ["PROVEEDORES"]
            lineas.append(f"- Proveedores registrados: {format_number_es(datos.get('proveedores_count', 0))}")
            secciones_vistas.add("PROVEEDORES")
            respuestas.append("\n".join(lineas))

    # --- MATERIALES / STOCK ---
    if has_keywords(check_strings, ["material", "materiales", "stock"]) and "ESTADO DEL INVENTARIO" not in secciones_vistas:
        lineas = ["ESTADO DEL INVENTARIO"]
        
        if has_keywords(check_strings, ["total", "hay", "cuantos", "cautnos", "cuántos", "que hay"]):
            lineas.append(f"- Tipos de materiales: {format_number_es(datos.get('total_materiales', 0))}")
        if has_keywords(check_strings, ["total stock", "total de stock"]):
            lineas.append(f"- Unidades totales en stock: {format_number_es(datos.get('total_stock', 0))}")
        
        if has_keywords(check_strings, ["poco", "bajo", "alerta", "alertas", "acabando", "terminando", "sin stock"]):
            if datos.get('stock_bajo', 0) > 0:
                lineas.append(f"- ⚠️ Materiales con stock bajo: {format_number_es(datos.get('stock_bajo', 0))}")
            else:
                lineas.append(f"- ✅ No hay materiales con stock bajo")
        
        if len(lineas) > 1:
            secciones_vistas.add("ESTADO DEL INVENTARIO")
            respuestas.append("\n".join(lineas))

    # --- VEHÍCULOS ---
    if has_keywords(check_strings, ["vehiculo", "vehiculos", "vehículo", "vehículos", "auto", "autos", "carro", "carros", "camion", "camiones", "conductor", "conductores", "asociado", "asignado"]) and "ESTADO DE VEHÍCULOS" not in secciones_vistas:
        lineas = ["ESTADO DE VEHÍCULOS"]
        
        incluir_resumen = has_keywords(check_strings, ["total", "hay", "cuantos", "cautnos", "cuántos", "vehiculo", "vehiculos", "vehículo", "vehículos", "conductor", "conductores"])
        incluir_asignacion = has_keywords(check_strings, ["asociado", "asignado", "cada conductor"])
        
        if incluir_resumen or incluir_asignacion:
            if incluir_resumen and has_keywords(check_strings, ["vehiculo", "vehiculos", "vehículo", "vehículos", "total", "hay", "cuantos", "cautnos", "cuántos"]):
                lineas.append(f"- Vehículos totales: {format_number_es(datos.get('vehiculos_count', 0))}")
                if has_keywords(check_strings, ["disponible", "disponibles", "libre", "libres"]):
                    lineas.append(f"- Vehículos disponibles: {format_number_es(datos.get('vehiculos_disponibles', 0))}")
                if has_keywords(check_strings, ["en ruta", "ruta", "ocupados"]):
                    lineas.append(f"- Vehículos en ruta: {format_number_es(datos.get('vehiculos_en_ruta', 0))}")
            if has_keywords(check_strings, ["conductor", "conductores", "total", "hay", "cuantos", "cautnos", "cuántos"]):
                lineas.append(f"- Conductores totales: {format_number_es(datos.get('conductor_count', 0))}")
            if incluir_asignacion:
                total_asignados = datos.get('total_conductores_con_vehiculo', 0)
                lineas.append(f"- Conductores con vehículo asignado: {format_number_es(total_asignados)}")
                
                if total_asignados > 0:
                    lineas.append(f"\nCONDUCTORES ASIGNADOS")
                    lista = datos.get('vehiculos_por_conductor_lista', [])
                    for idx, item in enumerate(lista, 1):
                        lineas.append(f"{item['nombre']} (Vehículo: {item['marca']} {item['modelo']} | Placa: {item['placa']})")
                
                total_conductores = datos.get('conductor_count', 0)
                if total_conductores > total_asignados:
                    lineas.append(f"\nOBSERVACIONES")
                    lineas.append(f"- Existen {format_number_es(total_conductores - total_asignados)} conductores sin vehículo asignado")
        
        if len(lineas) > 1:
            secciones_vistas.add("ESTADO DE VEHÍCULOS")
            respuestas.append("\n".join(lineas))

    # --- PEDIDOS ---
    if has_keywords(check_strings, ["pedido", "pedidos"]) and "ESTADO DE PEDIDOS" not in secciones_vistas:
        lineas = ["ESTADO DE PEDIDOS"]
        
        if has_keywords(check_strings, ["total", "hay", "cuantos", "cautnos", "cuántos"]):
            lineas.append(f"- Pedidos totales: {format_number_es(datos.get('pedidos_totales', 0))}")
        if has_keywords(check_strings, ["pendiente", "pendientes"]):
            lineas.append(f"- Pendientes: {format_number_es(datos.get('pedidos_pendientes', 0))}")
        if has_keywords(check_strings, ["aprobado", "aprobados"]):
            lineas.append(f"- Aprobados: {format_number_es(datos.get('pedidos_aprobados', 0))}")
        if has_keywords(check_strings, ["en camino", "camino"]):
            lineas.append(f"- En camino: {format_number_es(datos.get('pedidos_en_camino', 0))}")
        if has_keywords(check_strings, ["entregado", "entregados"]):
            lineas.append(f"- Entregados: {format_number_es(datos.get('pedidos_entregados', 0))}")
        if has_keywords(check_strings, ["cancelado", "cancelados"]):
            lineas.append(f"- Cancelados: {format_number_es(datos.get('pedidos_cancelados', 0))}")
        
        if has_keywords(check_strings, ["ventas", "total vendido", "ventas totales"]):
            lineas.append(f"\nVENTAS")
            lineas.append(f"- Total de ventas: {format_number_es(datos.get('total_ventas', 0))}")
        
        if len(lineas) > 1:
            secciones_vistas.add("ESTADO DE PEDIDOS")
            respuestas.append("\n".join(lineas))

    # --- COMPRAS ---
    if has_keywords(check_strings, ["compra", "compras"]) and "ESTADO DE COMPRAS" not in secciones_vistas:
        lineas = ["ESTADO DE COMPRAS"]
        
        if has_keywords(check_strings, ["total", "hay", "cuantos", "cautnos", "cuántos"]):
            lineas.append(f"- Compras totales: {format_number_es(datos.get('compras_totales', 0))}")
        if has_keywords(check_strings, ["pendiente", "pendientes"]):
            lineas.append(f"- Pendientes: {format_number_es(datos.get('compras_pendientes', 0))}")
        if has_keywords(check_strings, ["recibida", "recibidas"]):
            lineas.append(f"- Recibidas: {format_number_es(datos.get('compras_recibidas', 0))}")
        
        if has_keywords(check_strings, ["total compras", "total de compras"]):
            lineas.append(f"\nMONTOS")
            lineas.append(f"- Total de compras: {format_number_es(datos.get('total_compras', 0))}")
        
        if len(lineas) > 1:
            secciones_vistas.add("ESTADO DE COMPRAS")
            respuestas.append("\n".join(lineas))

    # --- FACTURAS ---
    if has_keywords(check_strings, ["factura", "facturas"]) and "ESTADO DE FACTURAS" not in secciones_vistas:
        lineas = ["ESTADO DE FACTURAS"]
        
        if has_keywords(check_strings, ["total", "hay", "cuantos", "cautnos", "cuántos"]):
            lineas.append(f"- Facturas totales: {format_number_es(datos.get('facturas_totales', 0))}")
        if has_keywords(check_strings, ["pendiente", "pendientes"]):
            lineas.append(f"- Pendientes: {format_number_es(datos.get('facturas_pendientes', 0))}")
        if has_keywords(check_strings, ["pagada", "pagadas"]):
            lineas.append(f"- Pagadas: {format_number_es(datos.get('facturas_pagadas', 0))}")
        
        if has_keywords(check_strings, ["total facturado", "facturado total"]):
            lineas.append(f"\nMONTOS")
            lineas.append(f"- Total facturado: {format_number_es(datos.get('total_facturado', 0))}")
        
        if len(lineas) > 1:
            secciones_vistas.add("ESTADO DE FACTURAS")
            respuestas.append("\n".join(lineas))

    # --- PAGOS ---
    if has_keywords(check_strings, ["pago", "pagos"]) and "ESTADO DE PAGOS" not in secciones_vistas:
        lineas = ["ESTADO DE PAGOS"]
        
        if has_keywords(check_strings, ["total", "hay", "cuantos", "cautnos", "cuántos"]):
            lineas.append(f"- Pagos registrados: {format_number_es(datos.get('pagos_totales', 0))}")
        if has_keywords(check_strings, ["total pagado", "pagado total"]):
            lineas.append(f"- Total pagado: {format_number_es(datos.get('total_pagado', 0))}")
        
        if len(lineas) > 1:
            secciones_vistas.add("ESTADO DE PAGOS")
            respuestas.append("\n".join(lineas))

    return respuestas


def verificar_pregunta_especifica(mensaje, usuario, historial, datos):
    """Verifica si la pregunta es específica y devuelve la respuesta (incluye múltiples partes)"""
    mensaje_lower = mensaje.lower()
    mensaje_normalizado = normalizar_texto(mensaje)
    es_primera_interaccion = len(historial) == 0
    respuestas = []
    secciones_vistas = set()

    # Construir saludo
    saludo = ""
    es_saludo = any(palabra in mensaje_normalizado for palabra in ["hola", "buenos dias", "buenas tardes", "buenas noches", "que tal", "como estas", "buen dia", "hey", "holi", "holis"])
    if es_primera_interaccion or es_saludo:
        saludo = "¡Hola!"
        if usuario and usuario.is_authenticated:
            saludo = f"¡Hola {usuario.nombres}!"

    # 1. Preprocesar: separar "y" que está pegado a palabras (ej: "conductory" → "conductor y")
    # Primero, manejar el caso específico "conductory"
    mensaje_procesado = re.sub(r'conductory', r'conductor y', mensaje_lower, flags=re.IGNORECASE)
    # Ahora, reemplazamos separadores claros
    mensaje_procesado = re.sub(r'\s+y que\s+', ' | ', mensaje_procesado, flags=re.IGNORECASE)
    mensaje_procesado = re.sub(r'\s+y qué\s+', ' | ', mensaje_procesado, flags=re.IGNORECASE)
    # NO reemplazamos solo "que" o "qué" para evitar romper preguntas como "cuantos proveedores hay"
    # Luego, reemplazamos " y " por " | " para separar las preguntas
    mensaje_procesado = re.sub(r'\s+y\s+', ' | ', mensaje_procesado, flags=re.IGNORECASE)

    # 3. Separar la pregunta en partes usando el separador " | " que creamos
    partes = mensaje_procesado.split(" | ")
    # Limpiar partes vacías o muy cortas
    partes = [p.strip() for p in partes if p.strip() and len(p.strip()) > 2]

    # 3. Procesar cada parte
    for parte in partes:
        parte_respuestas = procesar_parte_pregunta(parte, datos, secciones_vistas)
        respuestas.extend(parte_respuestas)

    # 4. Si no se procesaron partes, intentar con la pregunta ORIGINAL (no normalizada, para que procesar_parte_pregunta use both)
    if not respuestas:
        respuestas.extend(procesar_parte_pregunta(mensaje, datos, secciones_vistas))

    # 5. Resumen general si aún no hay respuestas
    if not respuestas and any(k in mensaje_normalizado for k in ["resumen", "sistema", "que hay", "qué hay", "que tiene", "qué tiene"]):
        if "RESUMEN DEL SISTEMA" not in secciones_vistas:
            secciones_vistas.add("RESUMEN DEL SISTEMA")
            respuestas.append(f"""RESUMEN DEL SISTEMA
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
            return f"{saludo}\n\n" + "\n\n".join(respuestas_unicas)
        return "\n\n".join(respuestas_unicas)

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
        respuesta_ayuda = """AYUDA

¿QUÉ PUEDO HACER?

- Hora y fecha: Preguntar la hora actual, incluyendo en otros países y zonas horarias
- Cálculos matemáticos: Realizar operaciones aritméticas básicas
- Información del sistema:
  - Usuarios, clientes y proveedores
  - Materiales y estado del inventario
  - Vehículos y asignaciones a conductores
  - Pedidos, compras, facturas y pagos

Puedes preguntar sobre cualquier aspecto del sistema o hacer preguntas generales!"""
        return f"{saludo}\n\n{respuesta_ayuda}".strip()

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
