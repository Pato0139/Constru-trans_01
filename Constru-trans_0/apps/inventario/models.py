
from django.db import models
from django.contrib.auth.models import User
from apps.usuarios.models import MaterialConstruccion


# =====================================================================
# MOVIMIENTO_INVENTARIO  (MER: #id_movimiento *cod_material -tipo_movimiento
#                        -cantidad -fecha *id_compra *codigo_pedido -observacion)
# =====================================================================
class MovimientoInventario(models.Model):
    TIPOS = [('entrada', 'Entrada'), ('salida', 'Salida')]

    id_movimiento = models.AutoField(primary_key=True)
    material = models.ForeignKey(MaterialConstruccion, on_delete=models.PROTECT,
                                 related_name='movimientos')
    tipo_movimiento = models.CharField(max_length=10, choices=TIPOS)
    cantidad = models.PositiveIntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    compra = models.ForeignKey('compras.Compra', on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='movimientos')
    pedido = models.ForeignKey('ordenes.Pedido', on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='movimientos')
    observacion = models.TextField(blank=True)

    # Fuera del MER pero útil — NO se toca
    usuario = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    sincronizado = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha']
        db_table = 'movimiento_inventario'

    def __str__(self):
        return f"{self.tipo_movimiento.upper()}: {self.cantidad} de {self.material.nombre}"
