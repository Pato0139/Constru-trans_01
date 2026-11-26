"""Base de conocimiento funcional completa del proyecto Constru-Trans.

Permite al asistente virtual responder preguntas sobre cualquier módulo, flujo,
regla de negocio, seguridad, infraestructura o funcionalidad del proyecto,
incluso cuando no hay conexión a un LLM externo.
"""

import re


def _normalizar(texto: str) -> str:
    texto = (texto or "").lower().strip()
    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }
    for orig, dest in reemplazos.items():
        texto = texto.replace(orig, dest)
    texto = re.sub(r"[^\w\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


# Entradas de conocimiento funcional completo del proyecto.
# Cada entrada tiene:
# - id: identificador único
# - triggers: frases o palabras de alta señal (peso 3)
# - keywords: palabras clave de apoyo (peso 1)
# - min_score: puntaje mínimo para activarse (evita falsos positivos en preguntas generales)
# - respuesta: función (usuario, datos) -> str o texto fijo
_CONOCIMIENTO_PROYECTO = [
    {
        "id": "captcha_login_seguridad",
        "triggers": [
            "captcha",
            "verificacion humana",
            "codigo de seguridad",
            "iniciar sesion",
            "inicio de sesion",
            "no puedo entrar",
            "no puedo iniciar sesion",
            "login",
        ],
        "keywords": ["imagen", "reto", "sesion", "acceso", "credenciales", "bloqueo"],
        "min_score": 3,
        "respuesta": (
            "🔐 **Inicio de sesión y CAPTCHA en Constru-Trans**\n"
            "- El acceso usa correo electrónico o usuario, contraseña y un **CAPTCHA real generado en el servidor** (imagen PNG con token en sesión).\n"
            "- Si el código no se lee bien, puedes pulsar el botón de **refrescar CAPTCHA** para generar una nueva imagen.\n"
            "- Si olvidaste tu contraseña, usa el enlace **¿Olvidaste tu contraseña?** en la pantalla de login para recibir un enlace seguro de restablecimiento por correo.\n"
            "- El sistema también registra intentos y eventos de seguridad en Auditoría."
        ),
    },
    {
        "id": "recuperar_cambiar_password",
        "triggers": [
            "cambiar contrasena",
            "cambiar mi contrasena",
            "cambio mi contrasena",
            "cambio de contrasena",
            "recuperar contrasena",
            "olvide mi contrasena",
            "olvidaste tu contrasena",
            "restablecer contrasena",
            "nueva contrasena",
            "cambiar clave",
            "cambio mi clave",
            "olvide mi clave",
        ],
        "keywords": ["password", "contrasena", "clave", "correo", "enlace", "token"],
        "min_score": 3,
        "respuesta": (
            "🔑 **Cambio y recuperación de contraseña**\n"
            "- **Si ya iniciaste sesión:** ve a **Mi Perfil** y haz clic en **Cambiar Contraseña**; se abrirá un modal seguro donde ingresas tu contraseña actual y la nueva (sin recargar ni cerrar sesión).\n"
            "- **Si olvidaste tu contraseña:** en la pantalla de inicio de sesión selecciona **Recuperar contraseña**, ingresa tu correo y abre el botón seguro del correo recibido.\n"
            "- La pantalla de nueva contraseña incluye indicador de fortaleza en tiempo real y validación de requisitos."
        ),
    },
    {
        "id": "mi_perfil_y_avatares",
        "triggers": [
            "mi perfil",
            "editar perfil",
            "foto de perfil",
            "cambiar foto",
            "subir foto",
            "avatar",
            "avatares",
            "foto con inicial",
            "letra en el perfil",
        ],
        "keywords": ["perfil", "foto", "imagen", "inicial", "color", "datos personales"],
        "min_score": 3,
        "respuesta": (
            "👤 **Mi Perfil y Avatares**\n"
            "- Cada rol (**Administrador**, **Cliente** y **Conductor**) cuenta con su propio panel de **Mi Perfil** con diseño ejecutivo de 2 columnas + franja inferior de credenciales y accesos directos.\n"
            "- **Avatares automáticos:** todo usuario nuevo recibe automáticamente una foto de perfil estilo Google con su inicial y color distintivo (generada con Pillow).\n"
            "- **Cambiar foto:** desde Mi Perfil haz clic en el ícono de cámara o en **Cambiar foto** para subir tu propia imagen (PNG, JPG o WEBP).\n"
            "- También puedes actualizar tus datos personales en **Editar Perfil** o cambiar tu contraseña desde el botón **Cambiar Contraseña**."
        ),
    },
    {
        "id": "bd_hibrida_sincronizacion_celador",
        "triggers": [
            "base de datos",
            "modo hibrido",
            "nube activa",
            "sqlite",
            "postgresql",
            "neon",
            "sincronizar",
            "sincronizacion",
            "celador",
            "sin internet",
            "offline",
            "backup",
            "copia de seguridad",
            "respaldo",
        ],
        "keywords": ["nube", "local", "bd", "db", "recuperacion", "descargar"],
        "min_score": 3,
        "respuesta": (
            "☁️ **Modo Híbrido (PostgreSQL + SQLite), Sincronización y Backups**\n"
            "- Constru-Trans funciona en **modo híbrido**: usa **PostgreSQL en la nube (Neon)** cuando hay conexión y mantiene una **copia local en SQLite3** para trabajar incluso sin internet.\n"
            "- **El Celador (sincronización automática):** mantiene sincronizados los cambios entre la nube y la base local automáticamente en segundo plano.\n"
            "- **Sincronización manual (Admin):** en **Mi Perfil > Gestión de Sistema** tienes el botón **Sincronizar Base Local** y en la barra superior el interruptor de **Nube activa**.\n"
            "- **Backup de recuperación (Admin):** puedes descargar un respaldo completo desde el Panel General en **Acciones Rápidas > Descargar Backup de Recuperación**."
        ),
    },
    {
        "id": "pagos_metodos_y_facturas",
        "triggers": [
            "metodos de pago",
            "metodo de pago",
            "como pagar",
            "como pago",
            "nequi",
            "daviplata",
            "bancolombia",
            "contraentrega",
            "comprobante",
            "pago rechazado",
            "correccion de pago",
            "corregir pago",
            "factura",
            "facturas",
            "facturacion",
        ],
        "keywords": ["pago", "pagos", "aprobar", "rechazar", "plazo", "evidencia", "recibo"],
        "min_score": 3,
        "respuesta": (
            "💳 **Pagos, Comprobantes y Facturación**\n"
            "- **Métodos aceptados:** Nequi, DaviPlata, Bancolombia (requieren subir comprobante en PNG/JPG) y **Contraentrega**.\n"
            "- **Revisión de pagos:** el administrador revisa el comprobante en **Pagos** y lo marca como *Aprobado* o *Rechazado*.\n"
            "- **Corrección de pago:** si un pago es rechazado, el cliente dispone de un plazo (12 horas, hasta 2 rechazos permitidos) para subir un nuevo comprobante antes de que el sistema cancele el pedido automáticamente.\n"
            "- **Facturas:** en el módulo de **Facturas** puedes consultar el número de factura, subtotal, impuestos, total, saldo pendiente y descargar el comprobante."
        ),
    },
    {
        "id": "tarifa_envio_y_pedidos_flujo",
        "triggers": [
            "tarifa de envio",
            "costo de envio",
            "valor de envio",
            "flete",
            "monto minimo",
            "minimo de pedido",
            "estados de pedido",
            "estados del pedido",
            "flujo de pedido",
            "flujo del pedido",
            "como funciona un pedido",
            "autorizado para despacho",
            "vehiculo asignado",
        ],
        "keywords": ["pedido", "envio", "despacho", "estado", "minimo", "subtotal", "cancelar"],
        "min_score": 3,
        "respuesta": (
            "📦 **Flujo de Pedidos, Mínimos y Tarifa de Envío**\n"
            "- **Cómo crear un pedido:** el cliente ingresa a **Nuevo Pedido**, elige materiales y cantidades, ingresa la dirección de destino y selecciona el método de pago.\n"
            "- **Tarifa de envío y mínimo:** el sistema calcula automáticamente el subtotal, valida el monto mínimo de compra y aplica la tarifa de envío según las reglas vigentes.\n"
            "- **Estados del pedido:**\n"
            "  1. *Pendiente*: esperando pago/validación.\n"
            "  2. *Autorizado para despacho*: pago aprobado o contraentrega confirmado.\n"
            "  3. *Vehículo asignado*: conductor y vehículo asignados por logística.\n"
            "  4. *En ruta*: el conductor inició el despacho.\n"
            "  5. *Entregado*: entrega confirmada en destino.\n"
            "  6. *Cancelado*: cancelado por cliente, admin o vencimiento de pago."
        ),
    },
    {
        "id": "logistica_entregas_novedades",
        "triggers": [
            "logistica",
            "asignar conductor",
            "asignar vehiculo",
            "como asigno",
            "mis entregas",
            "iniciar ruta",
            "finalizar entrega",
            "novedad",
            "novedades",
            "reportar novedad",
            "incidente en entrega",
            "flota",
        ],
        "keywords": ["vehiculo", "conductor", "entrega", "despacho", "placa", "mantenimiento"],
        "min_score": 3,
        "respuesta": (
            "🚛 **Logística, Flota, Entregas y Novedades**\n"
            "- **Vehículos:** el administrador registra placas, marca, modelo, tipo, capacidad de carga (toneladas) y estado (*Disponible*, *En Ruta*, *Mantenimiento*, *Fuera de Servicio*).\n"
            "- **Asignación:** en un pedido autorizado para despacho se asigna un conductor con vehículo disponible.\n"
            "- **Panel del Conductor:** el conductor ve sus entregas asignadas en **Mis Entregas**, confirma la salida (**Iniciar Ruta**) y marca la entrega como **Finalizada** al llegar.\n"
            "- **Novedades:** ante demoras, clima, fallas mecánicas, ausencia del cliente o problemas de vías, el conductor o admin puede registrar una **Novedad** con evidencia fotográfica y seguimiento."
        ),
    },
    {
        "id": "catalogo_inventario_movimientos",
        "triggers": [
            "catalogo",
            "tipos de material",
            "unidades de medida",
            "marcas de material",
            "movimientos de inventario",
            "entradas y salidas",
            "kardex",
            "stock minimo",
            "stock critico",
            "stock bajo",
        ],
        "keywords": ["material", "inventario", "stock", "marca", "unidad", "precio", "categoria"],
        "min_score": 3,
        "respuesta": (
            "🧱 **Catálogo, Inventario y Movimientos**\n"
            "- **Catálogo:** organiza los materiales por **Tipo de Material / Categoría**, **Marca** y **Unidad de Medida** (ej. bulto, m³, unidad, tonelada) con precio de referencia.\n"
            "- **Stock:** cada material controla su *cantidad actual* y *stock mínimo*. Cuando cae igual o por debajo del mínimo, aparece en alerta de stock crítico.\n"
            "- **Movimientos de Inventario:** toda compra recibida genera una **entrada** y cada pedido/despacho genera una **salida** con trazabilidad de usuario, fecha y observación."
        ),
    },
    {
        "id": "compras_y_proveedores",
        "triggers": [
            "compras",
            "proveedores",
            "orden de compra",
            "registrar compra",
            "agregar proveedor",
            "abastecimiento",
        ],
        "keywords": ["proveedor", "nit", "compra", "recibida", "pendiente", "insumos"],
        "min_score": 3,
        "respuesta": (
            "🏭 **Compras y Proveedores**\n"
            "- **Proveedores:** permite administrar empresas proveedoras con nombre, NIT, contacto, teléfono, correo y ciudad.\n"
            "- **Órdenes de Compra:** el administrador registra compras de materiales a un proveedor; al marcarse como **Recibida**, el sistema suma automáticamente las cantidades al inventario y crea el movimiento de entrada correspondiente."
        ),
    },
    {
        "id": "reportes_y_graficos",
        "triggers": [
            "reportes",
            "exportar pdf",
            "exportar excel",
            "exportar xml",
            "descargar reporte",
            "estadisticas",
            "grafico de ordenes",
            "graficos",
        ],
        "keywords": ["reporte", "pdf", "excel", "xml", "distribucion", "metricas", "exportacion"],
        "min_score": 3,
        "respuesta": (
            "📊 **Reportes y Exportación**\n"
            "- En el menú **Reportes** (exclusivo de Administración) puedes ver métricas consolidadas y el gráfico 2D de distribución de órdenes por estado.\n"
            "- Permite exportar reportes oficiales en **PDF**, **Excel (.xlsx)** y **XML** con los datos actualizados del sistema."
        ),
    },
    {
        "id": "auditoria_historial",
        "triggers": [
            "auditoria",
            "bitacora",
            "historial de actividades",
            "registro de acciones",
            "quien modifico",
            "quien elimino",
            "log de actividades",
        ],
        "keywords": ["historial", "accion", "modulo", "ip", "fecha", "trazabilidad"],
        "min_score": 3,
        "respuesta": (
            "📝 **Auditoría e Historial de Actividades**\n"
            "- El módulo **Auditoría** registra automáticamente las acciones clave (crear, editar, eliminar, inicio y cierre de sesión) junto con el usuario, módulo/tabla, fecha, hora y dirección IP.\n"
            "- Incluye barra de filtros instantáneos por búsqueda, acción y rango de fechas."
        ),
    },
    {
        "id": "filtros_ajax_accesibilidad_tema",
        "triggers": [
            "filtros",
            "filtro ajax",
            "buscar en tabla",
            "accesibilidad",
            "daltonismo",
            "modo oscuro",
            "modo claro",
            "tema oscuro",
            "tema claro",
            "tamano de letra",
            "tamano de texto",
        ],
        "keywords": ["protanopia", "deuteranopia", "tritanopia", "tema", "fuente", "buscador"],
        "min_score": 3,
        "respuesta": (
            "🎨 **Filtros Instantáneos, Temas y Accesibilidad**\n"
            "- **Filtros sin recarga (AJAX):** todas las tablas del sistema (Pedidos, Pagos, Facturas, Usuarios, Inventario, Vehículos, Compras y Auditoría) filtran al instante sin recargar la página y con validación de caracteres.\n"
            "- **Accesibilidad:** en la barra superior tienes el botón **Accesibilidad** con cambio entre **modo oscuro/claro**, ajuste de tamaño de fuente y filtros visuales para daltonismo (*protanopía*, *deuteranopía* y *tritanopía*)."
        ),
    },
    {
        "id": "ayuda_manuales_sugerencias",
        "triggers": [
            "centro de ayuda",
            "manual de usuario",
            "manual del administrador",
            "manual del cliente",
            "manual del conductor",
            "descargar manual",
            "enviar sugerencia",
            "sugerencias",
            "soporte tecnico",
        ],
        "keywords": ["ayuda", "manual", "guia", "sugerencia", "faq", "preguntas frecuentes"],
        "min_score": 3,
        "respuesta": (
            "❓ **Centro de Ayuda, Manuales y Sugerencias**\n"
            "- En **Ayuda** encuentras guías rápidas adaptadas a tu rol, preguntas frecuentes desplegables y la descarga del **Manual en PDF** correspondiente (Administrador, Cliente o Conductor).\n"
            "- También puedes enviar ideas, reportes de error o mejoras usando el botón **Enviar Sugerencia**."
        ),
    },
    {
        "id": "instalacion_setup_docker",
        "triggers": [
            "instalar proyecto",
            "como instalar",
            "setup windows",
            "setup linux",
            "setup macos",
            "docker",
            "docker compose",
            "correr el proyecto",
            "ejecutar el proyecto",
            "levantar servidor",
        ],
        "keywords": ["setup", "script", "contenedor", "venv", "entorno", "runserver"],
        "min_score": 3,
        "respuesta": (
            "⚙️ **Instalación y Ejecución de Constru-Trans**\n"
            "- **Windows:** ejecuta `setup/setup_windows.ps1` (crea `.venv`, instala dependencias, aplica migraciones y muestra el banner de Constru-Trans).\n"
            "- **macOS / Linux:** ejecuta `setup/setup_macos_linux.sh`.\n"
            "- **Docker:** el proyecto incluye `Dockerfile` y `docker-compose.yml` listos para levantar el servidor con `docker compose up --build`.\n"
            "- **Manual:** `python manage.py runserver` usando el entorno virtual `.venv`."
        ),
    },
    {
        "id": "roles_y_paneles",
        "triggers": [
            "que roles existen",
            "roles del sistema",
            "tipos de usuario",
            "permisos",
            "diferencia entre roles",
            "panel de administrador",
            "panel de cliente",
            "panel de conductor",
            "que modulos tiene",
            "todo lo que tiene el proyecto",
            "funciones del sistema",
            "funcionalidades del proyecto",
        ],
        "keywords": ["rol", "roles", "panel", "admin", "cliente", "conductor", "empleado", "modulos"],
        "min_score": 3,
        "respuesta": (
            "🏗️ **Roles y Módulos Completos de Constru-Trans**\n"
            "Constru-Trans integra 3 paneles principales adaptados a cada rol:\n"
            "- **Administrador / Empleado:** Dashboard con métricas, Usuarios y Conductores, Catálogo (Materiales, Tipos, Marcas, Unidades), Inventario y Movimientos, Pedidos, Pagos y Facturas, Compras y Proveedores, Flota y Logística, Reportes (PDF/Excel/XML), Auditoría, Backups y Sincronización Híbrida.\n"
            "- **Cliente:** Panel de Cliente, Nuevo Pedido (con cálculo de envío y mínimo), Mis Pedidos con seguimiento en tiempo real, Pagos/Comprobantes, Facturas, Mi Perfil y Centro de Ayuda.\n"
            "- **Conductor:** Panel del Conductor, Vehículo asignado, Mis Entregas (Iniciar Ruta / Finalizar Entrega), Reporte de Novedades, Mi Perfil y Centro de Ayuda.\n\n"
            "Pregúntame por cualquier módulo o dato en tiempo real (ej. *«¿qué pagos hay pendientes?»*, *«¿qué vehículos están disponibles?»*, *«¿cómo funciona el modo híbrido?»*)."
        ),
    },
]


def responder_conocimiento_proyecto(mensaje: str, usuario=None, datos=None):
    """Devuelve una respuesta precisa sobre cualquier funcionalidad del proyecto Constru-Trans.

    Retorna None si la pregunta no corresponde a conocimiento funcional del proyecto
    (por ejemplo, preguntas de cultura general), para que pase al LLM / búsqueda web.
    """
    norm = _normalizar(mensaje)
    if not norm or len(norm) < 3:
        return None

    mejor_entrada = None
    mejor_puntaje = 0

    for entrada in _CONOCIMIENTO_PROYECTO:
        puntaje = 0
        for trigger in entrada["triggers"]:
            if trigger in norm:
                puntaje += 3
        for kw in entrada["keywords"]:
            if re.search(rf"\b{re.escape(kw)}\b", norm):
                puntaje += 1
        if puntaje >= entrada["min_score"] and puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_entrada = entrada

    if not mejor_entrada:
        return None

    resp = mejor_entrada["respuesta"]
    return resp(usuario, datos) if callable(resp) else resp
