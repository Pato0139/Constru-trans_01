
from django.utils import timezone
from django.db.models import Sum, Count

try:
    from langchain_ollama import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    llm = ChatOllama(
        model="llama3.2"
    )

    # Importar todos los modelos
    from apps.usuarios.models import Usuario, MaterialConstruccion, Stock, Proveedor, Vehiculo
    from apps.clientes.models import Cliente
    from apps.gestion_pedidos.models import Pedido as PedidoGestion
    from apps.compras.models import Compra
    from apps.facturacion.models import Factura
    from apps.pagos.models import Pago

    def obtener_contexto_datos():
        """Obtiene datos relevantes completos del sistema para la IA"""
        try:
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
                # Calcular stock total
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
                
                # Total de ventas
                total_ventas = PedidoGestion.objects.aggregate(Sum('total'))['total__sum'] or 0
            except Exception as e:
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
            except:
                vehiculos_count = 0
                vehiculos_disponibles = 0
                vehiculos_en_ruta = 0
            
            # --- CLIENTES ---
            try:
                clientes_registrados = Cliente.objects.count()
            except:
                clientes_registrados = 0

            contexto = f"""
CONTEXTO COMPLETO DEL SISTEMA CONSTRU-TRANS (FECHA ACTUAL: {timezone.now()}):

--- DATOS GENERALES ---
NOMBRE DE LA EMPRESA: Constru-Trans
SISTEMA: Sistema de gestión de pedidos, inventario y transporte para materiales de construcción.

--- USUARIOS ---
- Total de usuarios: {total_usuarios}
- Usuarios activos: {usuarios_activos}
- Administradores: {admin_count}
- Clientes: {cliente_count}
- Conductores: {conductor_count}
- Empleados: {empleado_count}
- Clientes registrados: {clientes_registrados}

--- INVENTARIO ---
- Total de materiales: {total_materiales}
- Stock total (sumatoria): {total_stock} unidades
- Materiales con stock bajo: {stock_bajo}

--- PEDIDOS ---
- Total de pedidos: {pedidos_totales}
- Pendientes: {pedidos_pendientes}
- Aprobados: {pedidos_aprobados}
- En camino: {pedidos_en_camino}
- Entregados: {pedidos_entregados}
- Cancelados: {pedidos_cancelados}
- Total de ventas: ${total_ventas:,.2f}

--- COMPRAS ---
- Total de compras: {compras_totales}
- Pendientes: {compras_pendientes}
- Recibidas: {compras_recibidas}
- Total de compras: ${total_compras:,.2f}

--- FACTURAS ---
- Total de facturas: {facturas_totales}
- Pendientes de pago: {facturas_pendientes}
- Pagadas: {facturas_pagadas}
- Total facturado: ${total_facturado:,.2f}

--- PAGOS ---
- Total de pagos: {pagos_totales}
- Total pagado: ${total_pagado:,.2f}

--- PROVEEDORES ---
- Proveedores registrados: {proveedores_count}

--- VEHÍCULOS ---
- Vehículos totales: {vehiculos_count}
- Disponibles: {vehiculos_disponibles}
- En ruta: {vehiculos_en_ruta}

            """
            return contexto
        except Exception as e:
            return f"Error al cargar datos: {str(e)}"

    def preguntar_ia(mensaje, usuario=None):
        """Función principal para interactuar con la IA"""
        contexto = obtener_contexto_datos()
        
        # Añadir información del usuario al contexto si está autenticado
        nombre_usuario = ""
        if usuario and usuario.is_authenticated:
            nombre_usuario = f"{usuario.nombres} {usuario.apellidos}"
        
        system_prompt = """Eres el ASISTENTE VIRTUAL DE CONSTRU-TRANS. TU NO ERES EL USUARIO, TU ERES EL ASISTENTE.

REGLAS:
1. TU ERES: El asistente virtual de la empresa Constru-Trans
2. EL USUARIO ES: La persona que te está escribiendo (el cliente)
3. NO TE LLAMES COMO EL USUARIO, TU ERES EL ASISTENTE
4. SALUDA AL USUARIO POR SU NOMBRE SI LO TIENES
5. RESUELVE DUDAS SOBRE EL SISTEMA
6. NO INVENTES NADA QUE NO ESTÉ EN EL CONTEXTO
7. RESPONDE EN ESPAÑOL"""
        
        if nombre_usuario:
            system_prompt += f"\nNOMBRE DEL USUARIO (usa este nombre para saludar): {nombre_usuario}"
        
        system_prompt += f"\n\nCONTEXTO DEL SISTEMA:\n{contexto}"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}"),
        ])
        
        chain = prompt | llm | StrOutputParser()
        
        respuesta = chain.invoke({
            "input": mensaje
        })
        
        return respuesta

except ImportError:
    import random

    def preguntar_ia(mensaje, usuario=None):
        # Personalizar mensaje de bienvenida con el nombre del usuario
        saludo = "¡Hola!"
        if usuario and usuario.is_authenticated:
            saludo = f"¡Hola {usuario.nombres}!"
        
        respuestas = [
            f"{saludo} Soy tu asistente virtual de Constru-Trans. ¿En qué puedo ayudarte hoy?",
            f"{saludo} Estoy aquí para ayudarte con cualquier duda sobre inventario, pedidos o entregas.",
            f"{saludo} Recuerda que puedo ayudarte a consultar el estado de tus pedidos o el inventario disponible.",
            f"{saludo} Cuéntame qué necesitas y estaré feliz de ayudarte.",
            f"{saludo} Nota: Instala Ollama y langchain-ollama para obtener respuestas inteligentes."
        ]
        return random.choice(respuestas)
