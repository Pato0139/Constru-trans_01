from django.core.management.base import BaseCommand

from ia.services.rag_service import indexar_documentos


class Command(BaseCommand):
    help = "Indexa materiales y pedidos en ChromaDB para las consultas RAG"

    def handle(self, *args, **options):
        from ordenes.models import Pedido
        from usuarios.models import MaterialConstruccion

        documentos = []
        materiales = MaterialConstruccion.objects.filter(activo=True).select_related(
            "unidad_medida", "marca"
        )
        for material in materiales:
            documentos.append(
                {
                    "id": f"material-{material.cod_material}",
                    "texto": (
                        f"Material: {material.nombre}. "
                        f"Marca: {material.marca or 'Sin marca'}. "
                        f"Unidad: {material.unidad_medida}. "
                        f"Precio de referencia: {material.precio_referencia}. "
                        f"Descripción: {material.descripcion}"
                    ),
                    "metadata": {"tipo": "material"},
                }
            )

        pedidos = Pedido.objects.select_related("cliente").prefetch_related(
            "detalles__material"
        )[:200]
        for pedido in pedidos:
            materiales_pedido = ", ".join(
                detalle.material.nombre for detalle in pedido.detalles.all()[:10]
            )
            documentos.append(
                {
                    "id": f"pedido-{pedido.codigo_pedido}",
                    "texto": (
                        f"Pedido {pedido.codigo_pedido}, cliente {pedido.cliente or 'sin cliente'}, "
                        f"estado {pedido.estado}, total {pedido.total}, "
                        f"destino {pedido.direccion_destino}. "
                        f"Materiales: {materiales_pedido}"
                    ),
                    "metadata": {"tipo": "pedido"},
                }
            )

        cantidad = indexar_documentos(documentos)
        self.stdout.write(self.style.SUCCESS(f"Indexados {cantidad} documentos en ChromaDB."))
