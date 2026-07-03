import logging
import os

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    from httpx import Client

    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "local-key")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:latest")
    
    # Crear cliente HTTP personalizado con timeout corto (5 segundos) para no colgar el servidor
    http_client = Client(timeout=5.0)
    client = OpenAI(
        base_url=LLM_BASE_URL, 
        api_key=LLM_API_KEY,
        http_client=http_client
    )
except ImportError:
    client = None


def verificar_conexion_llm():
    if client is None:
        return False
    try:
        client.models.list()
        return True
    except Exception:
        logger.exception("No se pudo conectar al servidor LLM")
        return False


def construir_prompt_sistema(contexto, nombre_usuario):
    contexto_texto = "\n".join(f"- {k}: {v}" for k, v in contexto.items() if k != "generated_at")
    return f"""Eres el asistente virtual oficial de Constru-Trans.

Puedes responder dos tipos de preguntas:
1. Preguntas del sistema Constru-Trans (inventario, pedidos, compras, pagos, transporte, clientes, reportes).
2. Preguntas generales, triviales, educativas, conversacionales o cotidianas, aunque no tengan que ver con el sistema.

Reglas:
- Responde siempre en español.
- Si la pregunta usa datos del sistema, utiliza el contexto disponible.
- Si la pregunta NO usa datos del sistema, responde como un asistente general útil y natural.
- Si el usuario hace una continuación corta como "y en Bogotá", entiende que se refiere al tema anterior.
- No inventes datos internos del sistema.
- Para números grandes, usa punto como separador de miles y coma para decimales.
- Si algo no está claro, pide precisión sin responder de forma genérica vacía.

Usuario actual: {nombre_usuario or "No identificado"}

Datos actuales del sistema:
{contexto_texto}
""".strip()


def responder_fallback(mensaje, contexto, nombre_usuario):
    mensaje_lower = mensaje.lower().strip()
    
    # Saludos (incluidos "hi", "hello", "hey", "como estas", etc.)
    if any(greet in mensaje_lower for greet in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "saludos", "hi", "hello", "hey", "como estas", "cómo estás", "que tal", "qué tal"]):
        saludo = f"¡Hola {nombre_usuario or ''}! " if nombre_usuario else "¡Hola! "
        return saludo + "Soy el asistente virtual de Constru-Trans. En este momento el servidor de Inteligencia Artificial local (Ollama) no está activo, pero puedo darte datos en tiempo real del sistema. ¿En qué te puedo ayudar hoy?"
        
    # Preguntas sobre usuarios (verificando palabras completas o patrones para evitar falsos positivos con saludos cortos)
    if any(word in mensaje_lower for word in ["usuario", "conductor", "cliente", "admin", "empleado", "rol"]):
        total = contexto.get("total_usuarios", 0)
        activos = contexto.get("usuarios_activos", 0)
        clientes = contexto.get("cliente_count", 0)
        conductores = contexto.get("conductor_count", 0)
        admins = contexto.get("admin_count", 0)
        empleados = contexto.get("empleado_count", 0)
        return f"Aquí tienes la información de los usuarios del sistema:\n- Total de usuarios registrados: {total}\n- Usuarios activos: {activos}\n- Clientes registrados: {clientes}\n- Conductores contratados: {conductores}\n- Administradores: {admins}\n- Empleados: {empleados}."
        
    # Preguntas sobre pedidos
    if any(word in mensaje_lower for word in ["pedido", "orden", "venta"]):
        totales = contexto.get("pedidos_totales", 0)
        pendientes = contexto.get("pedidos_pendientes", 0)
        en_camino = contexto.get("pedidos_en_camino", 0)
        entregados = contexto.get("pedidos_entregados", 0)
        cancelados = contexto.get("pedidos_cancelados", 0)
        total_ventas = contexto.get("total_ventas", 0)
        top = contexto.get("top_cliente")
        
        resp = f"Resumen de Pedidos y Ventas:\n- Total de pedidos: {totales}\n- Pendientes de despacho: {pendientes}\n- Pedidos en ruta: {en_camino}\n- Pedidos entregados: {entregados}\n- Cancelados: {cancelados}\n- Facturación total por ventas: ${total_ventas:,.0f} COP."
        if top:
            resp += f"\n- Cliente con más pedidos: {top.get('nombre')} ({top.get('num_pedidos')} órdenes)."
        return resp
        
    # Preguntas sobre inventario o materiales
    if any(word in mensaje_lower for word in ["inventario", "material", "stock", "cemento", "arena", "ladrillo"]):
        materiales = contexto.get("total_materiales", 0)
        stock_total = contexto.get("total_stock", 0)
        stock_bajo = contexto.get("stock_bajo", 0)
        return f"Estado del Inventario de Materiales:\n- Tipos de materiales registrados: {materiales}\n- Stock total disponible: {stock_total} unidades\n- Materiales con stock crítico (bajo el mínimo): {stock_bajo}."
        
    # Preguntas sobre compras o proveedores
    if any(word in mensaje_lower for word in ["compra", "proveedor", "adquisicion"]):
        compras = contexto.get("compras_totales", 0)
        pendientes = contexto.get("compras_pendientes", 0)
        recibidas = contexto.get("compras_recibidas", 0)
        proveedores = contexto.get("proveedores_count", 0)
        total_compras = contexto.get("total_compras", 0)
        return f"Resumen de Abastecimiento:\n- Proveedores aliados registrados: {proveedores}\n- Total de órdenes de compra a proveedores: {compras}\n- Compras pendientes: {pendientes}\n- Compras recibidas: {recibidas}\n- Inversión total en compras: ${total_compras:,.0f} COP."

    # Preguntas sobre vehículos o entregas/transporte
    if any(word in mensaje_lower for word in ["vehiculo", "transporte", "camion", "placa", "conductor", "ruta"]):
        count = contexto.get("vehiculos_count", 0)
        disponibles = contexto.get("vehiculos_disponibles", 0)
        en_ruta = contexto.get("vehiculos_en_ruta", 0)
        asignados = contexto.get("total_conductores_con_vehiculo", 0)
        return f"Estado de la Flota y Transporte:\n- Vehículos totales: {count}\n- Disponibles: {disponibles}\n- En Ruta realizando entregas: {en_ruta}\n- Conductores con vehículos asignados: {asignados}."

    # Ayuda o comandos
    if any(word in mensaje_lower for word in ["ayuda", "que haces", "ayudame", "opciones", "saber"]):
        return "Puedo brindarte información en tiempo real de los siguientes módulos:\n1. **Usuarios y Personal** (roles, activos)\n2. **Pedidos y Facturación** (estados de pedidos, ventas totales)\n3. **Inventario** (materiales, stock crítico)\n4. **Compras y Proveedores**\n5. **Flota de Vehículos** (disponibles, asignaciones)\n\nEscribe sobre cualquiera de estos temas para consultarme directamente."

    return "En este momento el servidor de Inteligencia Artificial local (Ollama) está desconectado. Por favor, asegúrate de iniciar Ollama en tu computadora y descargar el modelo `llama3.2` para habilitar el chat general interactivo. Mientras tanto, puedes consultarme datos en tiempo real sobre usuarios, pedidos, inventario, compras o vehículos del sistema."


def preguntar_llm(mensaje, contexto, nombre_usuario, historial):
    # Extraer el mensaje real del usuario si viene con memoria semántica enriquecida
    mensaje_real = mensaje
    if "Pregunta del usuario:" in mensaje:
        parts = mensaje.split("Pregunta del usuario:")
        if len(parts) > 1:
            mensaje_real = parts[1].strip()

    if client is None:
        logger.error("Cliente LLM no está disponible (openai no instalado)")
        return responder_fallback(mensaje_real, contexto, nombre_usuario)

    system_prompt = construir_prompt_sistema(contexto, nombre_usuario)

    messages = [{"role": "system", "content": system_prompt}]

    for msg in (historial or [])[-12:]:
        role = "user" if msg.get("role") == "user" or msg.get("sender") == "user" else "assistant"
        text = (msg.get("content") or msg.get("text") or "").strip()
        if text:
            messages.append({"role": role, "content": text[:1200]})

    messages.append({"role": "user", "content": mensaje[:3000]})

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL, messages=messages, temperature=0.3
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception:
        logger.exception("Error consultando servidor LLM, activando fallback local")
        return responder_fallback(mensaje_real, contexto, nombre_usuario)


