from dataclasses import dataclass
from datetime import datetime
import logging
import unicodedata

from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Q, Sum
from django.urls import reverse
from django.utils import timezone

from apps.catalogo.models import MaterialConstruccion as Material
from apps.catalogo.models import Stock
from config.db_preference import debe_usar_bd_remota

from ..models import MovimientoInventario

logger = logging.getLogger(__name__)


# Umbrales de bajo stock generalizados para los 20 tipos de material existentes (TM001–TM020)
UMBRALES_POR_CODIGO_TIPO: dict[str, int] = {
    "TM001": 1000,  # Materiales de Construcción (ladrillos, bloques, adoquines, tejas)
    "TM002": 20,    # Agregados (arena, grava, triturado en m3/ton)
    "TM003": 100,   # Cementos y Morteros (bultos/bolsas)
    "TM004": 100,   # Aceros y Metales (varillas, perfiles, alambre)
    "TM005": 50,    # Tuberías y Conexiones (tubos PVC, codos, uniones)
    "TM006": 40,    # Material Eléctrico (cables, interruptores, breakers)
    "TM007": 30,    # Material Hidráulico (válvulas, registros, grifería)
    "TM008": 25,    # Pinturas y Recubrimientos (galones, cuñetes, impermeabilizantes)
    "TM009": 30,    # Madera y Derivados (tablas, listones, formaletas)
    "TM010": 10,    # Herramientas (palas, picas, martillos, equipos manuales)
    "TM011": 20,    # Equipos de Seguridad (EPP) (cascos, guantes, botas, gafas)
    "TM012": 50,    # Ferretería General (puntillas, tornillos, clavos, chazos, tuercas)
    "TM013": 15,    # Lubricantes y Aceites (aceites, grasas, refrigerantes)
    "TM014": 50,    # Combustibles (galones de ACPM/gasolina)
    "TM015": 10,    # Repuestos de Vehículos (filtros, pastillas, correas)
    "TM016": 8,     # Llantas y Accesorios (llantas, neumáticos)
    "TM017": 15,    # Material de Oficina (resmas, papelería)
    "TM018": 40,    # Consumibles (discos de corte, lijas, soldadura, cintas)
    "TM019": 5,     # Equipos y Maquinaria (mezcladoras, compactadoras, vibradores)
    "TM020": 15,    # Señalización y Seguridad Vial (conos, cintas de peligro, vallas)
}

UMBRALES_POR_NOMBRE_TIPO: dict[str, int] = {
    "materiales de construccion": 1000,
    "agregados": 20,
    "cementos y morteros": 100,
    "aceros y metales": 100,
    "tuberias y conexiones": 50,
    "material electrico": 40,
    "material hidraulico": 30,
    "pinturas y recubrimientos": 25,
    "madera y derivados": 30,
    "herramientas": 10,
    "equipos de seguridad (epp)": 20,
    "equipos de seguridad": 20,
    "ferreteria general": 50,
    "lubricantes y aceites": 15,
    "combustibles": 50,
    "repuestos de vehiculos": 10,
    "llantas y accesorios": 8,
    "material de oficina": 15,
    "consumibles": 40,
    "equipos y maquinaria": 5,
    "senalizacion y seguridad vial": 15,
}

# Reglas específicas por palabras clave del producto: (palabras_clave, umbral, etiqueta_tipo)
REGLAS_PALABRAS_CLAVE: list[tuple[tuple[str, ...], int, str]] = [
    (
        ("ladrillo", "bloque", "adoquin", "teja", "baldosa", "enchape", "tableta", "mamposteria"),
        1000,
        "Materiales de Construcción",
    ),
    (
        (
            "puntilla",
            "clavo",
            "tornillo",
            "chazo",
            "tuerca",
            "arandela",
            "remache",
            "grapa",
            "bisagra",
            "candado",
            "chapeta",
        ),
        50,
        "Ferretería General",
    ),
    (
        ("cemento", "mortero", "estuco", "yeso", "cal ", "pegacor", "boquilla", "concreto"),
        100,
        "Cementos y Morteros",
    ),
    (
        ("varilla", "acero", "alambre", "malla", "perfil", "angulo", "platina", "viga", "fleje"),
        100,
        "Aceros y Metales",
    ),
    (
        ("arena", "grava", "gravilla", "triturado", "recebo", "piedra", "balasto", "afirmado"),
        20,
        "Agregados",
    ),
    (
        ("tubo", "tuberia", "codo", "tee", "union", "buje", "adaptador", "sifon", "pvc"),
        50,
        "Tuberías y Conexiones",
    ),
    (
        ("valvula", "registro", "griferia", "llave de paso", "cheque", "hidraulico"),
        30,
        "Material Hidráulico",
    ),
    (
        ("cable", "interruptor", "tomacorriente", "breaker", "taco", "bombillo", "luminaria", "conduit"),
        40,
        "Material Eléctrico",
    ),
    (
        ("pintura", "vinilo", "esmalte", "anticorrosivo", "barniz", "impermeabilizante", "sellador", "thinner"),
        25,
        "Pinturas y Recubrimientos",
    ),
    (
        ("madera", "tabla", "liston", "formaleta", "triplex", "guadua", "vareta", "polin"),
        30,
        "Madera y Derivados",
    ),
    (
        ("pala", "pica", "martillo", "alicate", "destornillador", "segueta", "palustre", "llana", "carretilla", "taladro", "pulidora"),
        10,
        "Herramientas",
    ),
    (
        ("casco", "guante", "bota", "gafa", "careta", "arnes", "eslinga", "tapabocas", "chaleco"),
        20,
        "Equipos de Seguridad (EPP)",
    ),
    (
        ("aceite", "lubricante", "grasa", "refrigerante", "liquido de frenos"),
        15,
        "Lubricantes y Aceites",
    ),
    (
        ("acpm", "diesel", "gasolina", "combustible"),
        50,
        "Combustibles",
    ),
    (
        ("llanta", "neumatico", "rin"),
        8,
        "Llantas y Accesorios",
    ),
    (
        ("repuesto", "filtro", "pastilla", "banda", "bujia", "amortiguador", "bateria", "correa"),
        10,
        "Repuestos de Vehículos",
    ),
    (
        ("resma", "papel", "carpeta", "oficina", "marcador", "talonario"),
        15,
        "Material de Oficina",
    ),
    (
        ("disco", "lija", "soldadura", "electrodo", "cinta", "teflon", "silicona"),
        40,
        "Consumibles",
    ),
    (
        ("mezcladora", "trompo", "compactadora", "rana", "canguro", "vibrador", "planta electrica", "compresor", "andamio"),
        5,
        "Equipos y Maquinaria",
    ),
    (
        ("cono", "senal", "valla", "delineador", "demarcacion", "peligro"),
        15,
        "Señalización y Seguridad Vial",
    ),
]


def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    norm = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in norm if not unicodedata.combining(c)).lower().strip()


def obtener_etiqueta_tipo_material(material) -> str:
    """Devuelve el nombre del tipo de material (desde Catalogo o inferido por nombre)."""
    if material is None:
        return "General"
    catalogo = getattr(material, "catalogo", None)
    if catalogo and getattr(catalogo, "nombre_empresa", ""):
        return catalogo.nombre_empresa

    texto = _normalizar_texto(f"{getattr(material, 'nombre', '')} {getattr(material, 'descripcion', '')}")
    for palabras, _umbral, etiqueta in REGLAS_PALABRAS_CLAVE:
        if any(p in texto for p in palabras):
            return etiqueta
    return "Materiales de Construcción"


def calcular_umbral_stock_bajo(material) -> int:
    """
    Calcula el umbral de stock mínimo/bajo de forma generalizada según el tipo de material,
    el producto específico y su unidad de medida:
      - Ej. Ladrillos / bloques / mampostería (TM001): 1000 unidades
      - Ej. Puntillas / tornillos / ferretería general (TM012): 50 unidades
      - Ej. Cementos y morteros (TM003): 100 bultos
      - Ej. Agregados en m3/ton (TM002): 20 m3
      - Y así para los 20 tipos del catálogo (TM001–TM020).
    """
    if material is None:
        return 30

    texto = _normalizar_texto(f"{getattr(material, 'nombre', '')} {getattr(material, 'descripcion', '')}")

    # 1. Coincidencia específica por producto (garantiza que ej. ladrillo=1000 y puntilla=50 siempre)
    for palabras, umbral, _etiqueta in REGLAS_PALABRAS_CLAVE:
        if any(p in texto for p in palabras):
            return umbral

    # 2. Coincidencia por tipo de material (Catalogo TM001–TM020 por código o por nombre)
    catalogo = getattr(material, "catalogo", None)
    unidad = getattr(material, "unidad_medida", None)
    unidad_cod = _normalizar_texto(
        f"{getattr(unidad, 'codigo', '')} {getattr(unidad, 'nombre', '')} {getattr(unidad, 'abreviatura', '')}"
    )

    if catalogo:
        codigo_cat = (getattr(catalogo, "codigo_catalogo", "") or "").strip().upper()
        nombre_cat = _normalizar_texto(getattr(catalogo, "nombre_empresa", ""))

        umbral_cat = UMBRALES_POR_CODIGO_TIPO.get(codigo_cat) or UMBRALES_POR_NOMBRE_TIPO.get(nombre_cat)
        if umbral_cat is not None:
            # Si es TM001 general pero se mide en m3/toneladas o bultos, ajustar proporcionalmente
            if codigo_cat == "TM001" or nombre_cat == "materiales de construccion":
                if any(u in unidad_cod for u in ("m3", "metro cubico", "ton")):
                    return 20
                if any(u in unidad_cod for u in ("bto", "bulto", "bolsa", "saco")):
                    return 100
            return umbral_cat

    # 3. Respaldo por unidad de medida
    if any(u in unidad_cod for u in ("m3", "metro cubico", "ton")):
        return 20
    if any(u in unidad_cod for u in ("bto", "bulto", "bolsa", "saco")):
        return 100
    if any(u in unidad_cod for u in ("kg", "kilo", "mt", "metro", "m2")):
        return 50
    if any(u in unidad_cod for u in ("gl", "galon", "lt", "litro")):
        return 20

    return 50


def evaluar_y_notificar_stock_bajo(
    material,
    cantidad_actual: int,
    cantidad_anterior: int | None = None,
    umbral: int | None = None,
):
    """
    Evalúa si el stock actual de un material cayó en o por debajo del umbral de su tipo
    (o se agotó) y genera/actualiza la notificación para los administradores activos.
    Si el stock se reabastece por encima del umbral, marca las alertas previas como leídas.
    """
    if material is None or not getattr(material, "pk", None):
        return

    from apps.usuarios.models import Notificacion, Usuario

    if umbral is None or umbral <= 0:
        umbral = calcular_umbral_stock_bajo(material)

    tipo_label = obtener_etiqueta_tipo_material(material)
    unidad = getattr(material, "unidad_medida", None)
    unidad_label = (
        getattr(unidad, "abreviatura", None)
        or getattr(unidad, "nombre", None)
        or "unidades"
    )

    try:
        link_stock = f"{reverse('catalogo:stock_lista')}?q={material.nombre}"
    except Exception:
        link_stock = "/catalogo/stock/"

    titulo_bajo = f"Stock bajo - {material.nombre}"
    titulo_agotado = f"¡Stock agotado! - {material.nombre}"

    # Obtener administradores activos en la base 'default' (donde vive la app usuarios/notificaciones)
    admins = list(
        Usuario.objects.using("default")
        .filter(Q(rol="admin") | Q(is_superuser=True), is_active=True)
        .exclude(estado__in=["inactivo", "suspendido"])
        .order_by("id")
    )
    if not admins:
        return

    # Caso 1: Stock reabastecido por encima del umbral -> cerrar alertas pendientes de este material
    if cantidad_actual > umbral:
        actualizadas = (
            Notificacion.objects.using("default")
            .filter(
                usuario__in=admins,
                titulo__in=[titulo_bajo, titulo_agotado],
                leida=False,
            )
            .update(leida=True)
        )
        if actualizadas:
            for adm in admins:
                cache.delete(f"notif_user_{adm.pk}")
        return

    # Caso 2: Stock en o por debajo del umbral (0 < cantidad_actual <= umbral o cantidad_actual == 0)
    # Solo disparamos cuando baja el stock o cuando aún no existe alerta activa sin leer.
    bajo_o_cambio = (
        cantidad_anterior is None
        or cantidad_actual < cantidad_anterior
        or (cantidad_anterior > umbral and cantidad_actual <= umbral)
    )

    if cantidad_actual <= 0:
        titulo = titulo_agotado
        mensaje = (
            f"¡Atención! El producto «{material.nombre}» ({tipo_label}) se ha agotado "
            f"(0 {unidad_label} disponibles). El mínimo para este tipo de material es "
            f"{umbral} {unidad_label}."
        )
    else:
        titulo = titulo_bajo
        mensaje = (
            f"Queda poco stock de «{material.nombre}» ({tipo_label}): quedan "
            f"{cantidad_actual} {unidad_label} disponibles (umbral mínimo para este tipo: "
            f"{umbral} {unidad_label}). Se recomienda reabastecer."
        )

    ahora = timezone.now()
    for adm in admins:
        notif_no_leida = (
            Notificacion.objects.using("default")
            .filter(
                usuario=adm,
                titulo__in=[titulo_bajo, titulo_agotado],
                leida=False,
            )
            .first()
        )
        if notif_no_leida:
            if (
                notif_no_leida.titulo != titulo
                or notif_no_leida.mensaje != mensaje
                or bajo_o_cambio
            ):
                notif_no_leida.titulo = titulo
                notif_no_leida.mensaje = mensaje
                notif_no_leida.tipo = "warning"
                notif_no_leida.link = link_stock
                notif_no_leida.fecha = ahora
                notif_no_leida.save(
                    using="default",
                    update_fields=["titulo", "mensaje", "tipo", "link", "fecha"],
                )
                cache.delete(f"notif_user_{adm.pk}")
        elif bajo_o_cambio:
            Notificacion.objects.using("default").create(
                usuario=adm,
                titulo=titulo,
                mensaje=mensaje,
                tipo="warning",
                link=link_stock,
            )
            cache.delete(f"notif_user_{adm.pk}")



@dataclass
class ResumenKardex:
    material_id: int
    entradas: int
    salidas: int
    ajustes: int
    saldo_actual: int
    periodo_inicio: datetime
    periodo_fin: datetime


class KardexService:
    @staticmethod
    def get_db_alias():
        return "remota" if debe_usar_bd_remota() else "default"

    @classmethod
    def registrar_movimiento(
        cls,
        *,
        material_id: int,
        tipo: str,
        cantidad: int,
        observacion: str = "",
        usuario=None,
        compra_id: int | None = None,
        pedido_id: int | None = None,
        using: str | None = None,
    ) -> MovimientoInventario:
        if tipo not in ("entrada", "salida", "ajuste"):
            raise ValueError(f"Tipo inválido: {tipo}. Use 'entrada'|'salida'|'ajuste'.")
        if cantidad <= 0:
            raise ValueError("Cantidad debe ser mayor a 0.")

        db_alias = using or cls.get_db_alias()

        with transaction.atomic(using=db_alias):
            from config.db_utils import select_for_update_if_supported

            material = select_for_update_if_supported(
                Material.objects.using(db_alias), db_alias
            ).get(pk=material_id)
            stock, _ = (
                select_for_update_if_supported(Stock.objects.using(db_alias), db_alias)
                .using(db_alias)
                .get_or_create(material=material, defaults={"cantidad_actual": 0})
            )

            if tipo == "entrada":
                stock.cantidad_actual += cantidad
            elif tipo == "salida":
                if stock.cantidad_actual < cantidad:
                    raise ValueError(
                        f"Stock insuficiente para {material.nombre}: "
                        f"disponible={stock.cantidad_actual}, requerido={cantidad}"
                    )
                stock.cantidad_actual -= cantidad
            else:
                if cantidad < 0:
                    raise ValueError("La cantidad de ajuste no puede ser negativa.")
                stock.cantidad_actual = cantidad

            stock.save(using=db_alias)
            stock.refresh_from_db(using=db_alias)

            if tipo == "ajuste":
                tipo_a_guardar = "salida" if cantidad < stock.cantidad_actual else "entrada"
            else:
                tipo_a_guardar = tipo

            return MovimientoInventario.objects.using(db_alias).create(
                material=material,
                tipo_movimiento=tipo_a_guardar,
                cantidad=cantidad,
                observacion=observacion,
                usuario=usuario,
                compra_id=compra_id,
                pedido_id=pedido_id,
            )

    @classmethod
    def resumen_periodo(
        cls, material_id: int, fecha_inicio: datetime, fecha_fin: datetime
    ) -> ResumenKardex:
        qs = MovimientoInventario.objects.filter(
            material_id=material_id,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin,
        )
        entradas = qs.filter(tipo_movimiento="entrada").aggregate(t=Sum("cantidad"))["t"] or 0
        salidas = qs.filter(tipo_movimiento="salida").aggregate(t=Sum("cantidad"))["t"] or 0
        try:
            saldo = Stock.objects.get(material_id=material_id).cantidad_actual
        except Stock.DoesNotExist:
            saldo = 0

        return ResumenKardex(
            material_id=material_id,
            entradas=entradas,
            salidas=salidas,
            ajustes=0,
            saldo_actual=saldo,
            periodo_inicio=fecha_inicio,
            periodo_fin=fecha_fin,
        )

    @classmethod
    def alertas_stock_bajo(cls, umbral: int = 10):
        return (
            Stock.objects.select_related("material")
            .filter(cantidad_actual__lte=umbral)
            .order_by("cantidad_actual")
        )


class StockService:
    @staticmethod
    def stock_actual(material_id: int) -> int:
        try:
            return Stock.objects.get(material_id=material_id).cantidad_actual
        except Stock.DoesNotExist:
            return 0

    @classmethod
    def obtener_materiales_sin_stock(cls) -> list[Material]:
        return list(
            Material.objects.filter(stock_info__cantidad_actual__lte=0).select_related("stock_info")
        )
