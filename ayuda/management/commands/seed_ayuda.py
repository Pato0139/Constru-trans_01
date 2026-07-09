from django.core.management.base import BaseCommand
from ayuda.models import CategoriaAyuda, GuiaEdicion, PasoGuia, ColorSistema


GUIAS = [
    {
        "categoria": ("Primeros pasos", "Guías básicas para usuarios nuevos", 1),
        "titulo": "Cómo usar ConstruTrans por primera vez",
        "contenido": (
            "Esta guía explica cómo entrar al sistema, identificar el menú principal, "
            "usar el panel de control y localizar las secciones más importantes."
        ),
        "orden": 1,
        "favorito": True,
        "pasos": [
            ("Entrar al panel", "Inicia sesión con tu correo y contraseña."),
            ("Ubicar el menú lateral", "Usa el menú izquierdo para navegar por módulos."),
            ("Identificar tu rol", "Tu panel cambia si eres admin, cliente o conductor."),
            ("Usar el botón principal", "Empieza siempre por la acción principal del panel."),
        ],
    },
    {
        "categoria": ("Pedidos", "Flujo de pedidos y seguimiento", 2),
        "titulo": "Cómo solicitar un pedido",
        "contenido": (
            "Aprende a crear un pedido, elegir materiales, confirmar cantidades "
            "y hacer seguimiento al estado."
        ),
        "orden": 1,
        "favorito": True,
        "pasos": [
            ("Ir a Solicitar Pedido", "Desde el menú lateral entra en Solicitar Pedido."),
            ("Elegir materiales", "Selecciona los productos y cantidades."),
            ("Confirmar datos", "Revisa dirección, observaciones y total."),
            ("Enviar solicitud", "Pulsa guardar o enviar para registrar el pedido."),
        ],
    },
    {
        "categoria": ("Perfil y cuenta", "Configuración personal del usuario", 3),
        "titulo": "Cómo editar tu perfil",
        "contenido": (
            "Explica qué datos puedes actualizar y cuáles son informativos, "
            "como el documento de identidad."
        ),
        "orden": 1,
        "favorito": False,
        "pasos": [
            ("Abrir Mi Cuenta", "Entra en la sección de perfil desde el menú."),
            ("Editar campos permitidos", "Actualiza nombres, apellidos, correo y teléfono."),
            ("Documento bloqueado", "El documento se muestra pero no se puede modificar."),
            ("Guardar cambios", "Pulsa guardar para actualizar tu perfil."),
        ],
    },
    {
        "categoria": ("Pagos y facturas", "Consultas de facturación y pagos", 4),
        "titulo": "Cómo revisar pagos y facturas",
        "contenido": (
            "Aprende dónde consultar el historial de pagos, el estado de las facturas "
            "y los comprobantes asociados."
        ),
        "orden": 1,
        "favorito": False,
        "pasos": [
            ("Abrir Mis Pagos", "Ve a la sección de pagos desde el menú."),
            ("Filtrar resultados", "Usa el buscador o filtros disponibles."),
            ("Ver factura", "Abre la factura vinculada al pago."),
            ("Descargar comprobantes", "Si existe PDF, descargalo desde la acción correspondiente."),
        ],
    },
]


COLORES = [
    ("Fondo claro", "#F8FAFC", "Tema claro", "Fondos principales del modo claro"),
    ("Fondo oscuro", "#0B0D12", "Tema oscuro", "Fondos principales del modo oscuro"),
    ("Contraste alto", "#FFD600", "Accesibilidad", "Resaltado principal del modo accesible"),
    ("Texto principal", "#FFFFFF", "Accesibilidad", "Texto de alto contraste"),
]


class Command(BaseCommand):
    help = "Carga guías iniciales y colores del centro de ayuda"

    def handle(self, *args, **options):
        for nombre, descripcion, orden in {
            item["categoria"] for item in GUIAS
        }:
            CategoriaAyuda.objects.get_or_create(
                nombre=nombre,
                defaults={"descripcion": descripcion, "orden": orden},
            )

        for item in GUIAS:
            categoria = CategoriaAyuda.objects.get(nombre=item["categoria"][0])

            guia, _ = GuiaEdicion.objects.update_or_create(
                titulo=item["titulo"],
                defaults={
                    "categoria": categoria,
                    "contenido": item["contenido"],
                    "orden": item["orden"],
                    "es_favorito": item["favorito"],
                    "activo": True,
                },
            )

            guia.pasos.all().delete()
            for idx, (titulo_paso, descripcion) in enumerate(item["pasos"], start=1):
                PasoGuia.objects.create(
                    guia=guia,
                    numero_paso=idx,
                    titulo_paso=titulo_paso,
                    descripcion=descripcion,
                )

        for nombre, codigo_hex, descripcion, uso in COLORES:
            ColorSistema.objects.update_or_create(
                nombre=nombre,
                defaults={
                    "codigo_hex": codigo_hex,
                    "descripcion": descripcion,
                    "uso": uso,
                    "activo": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("✅ Centro de ayuda inicial cargado correctamente"))
