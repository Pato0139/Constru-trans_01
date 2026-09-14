from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError

from ia.services.rag_service import indexar_documentos


class Command(BaseCommand):
    help = "Indexa materiales y pedidos en ChromaDB para las consultas RAG"

    def handle(self, *args, **options):
        from ordenes.models import Pedido
        from usuarios.models import MaterialConstruccion

        documentos = []
        try:
            for material in MaterialConstruccion.objects.filter(activo=True).select_related("unidad_medida"):
                documentos.append(
                    {
                        "id": f"material-{material.cod_material}",
                        "texto": (
                            f"Material: {material.nombre}. "
                            f"Unidad: {material.unidad_medida}. Precio: {material.precio_referencia}. "
                            f"Descripción: {material.descripcion}"
                        ),
                        "metadata": {"tipo": "material"},
                    }
                )

            for pedido in Pedido.objects.select_related("cliente").prefetch_related("detalles__material")[:200]:
                cliente_texto = (
                    f"cliente #{pedido.cliente_id}"
                    if pedido.cliente_id
                    else "sin cliente"
                )
                materiales_validos = []
                detalles_huerfanos = 0
                for detalle in pedido.detalles.all()[:10]:
                    try:
                        materiales_validos.append(detalle.material.nombre)
                    except MaterialConstruccion.DoesNotExist:
                        detalles_huerfanos += 1
                materiales = ", ".join(materiales_validos) or "sin materiales válidos"
                if detalles_huerfanos:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Pedido {pedido.codigo_pedido}: se omitieron "
                            f"{detalles_huerfanos} detalles sin material válido."
                        )
                    )
                documentos.append(
                    {
                        "id": f"pedido-{pedido.codigo_pedido}",
                        "texto": (
                            f"Pedido {pedido.codigo_pedido}, {cliente_texto}, "
                            f"estado {pedido.estado}, total {pedido.total}, destino {pedido.direccion_destino}. "
                            f"Materiales: {materiales}"
                        ),
                        "metadata": {"tipo": "pedido"},
                    }
                )
        except OperationalError as exc:
            raise CommandError(
                "No se pudo leer la base de datos. Ejecuta primero las migraciones "
                f"locales y verifica el esquema: {exc}"
            ) from exc

        cantidad = indexar_documentos(documentos)
        self.stdout.write(self.style.SUCCESS(f"Indexados {cantidad} documentos en ChromaDB."))
