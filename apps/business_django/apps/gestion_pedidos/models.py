from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.utils import timezone
from apps.usuarios.models import Usuario, MaterialConstruccion

class Pedido(models.Model):
    """Encabezado del pedido."""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('cancelado', 'Cancelado'),
        ('en_camino', 'En camino'),
        ('entregado', 'Entregado'),
    ]

    cliente = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='pedidos_gestion',
        help_text='Cliente que crea el pedido.'
    )
    fecha_creacion = models.DateTimeField(default=timezone.now, editable=False)
    estado = models.CharField(
        max_length=12,
        choices=ESTADO_CHOICES,
        default='pendiente',
        help_text='Estado del ciclo de vida del pedido.'
    )
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Descuento global aplicado al total bruto.'
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False,
        help_text='Total neto después de aplicar descuento.'
    )

    class Meta:
        db_table = 'gestion_pedido'
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'Pedido #{self.id} – {self.cliente}'

    def calcular_total(self):
        """Recalcula y guarda el total del pedido."""
        bruto = sum(det.subtotal for det in self.detalles.all())
        self.total = max(bruto - self.descuento, 0)
        self.save(update_fields=['total'])
        return self.total

class DetallePedido(models.Model):
    """Detalle de línea de un pedido."""
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    material = models.ForeignKey(
        MaterialConstruccion,
        on_delete=models.PROTECT,
        related_name='detalles_pedidos_gestion',
        help_text='Material solicitado.'
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text='Cantidad solicitada.'
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Precio unitario al momento del pedido.'
    )

    class Meta:
        db_table = 'gestion_detalle_pedido'
        verbose_name = 'Detalle de Pedido'
        verbose_name_plural = 'Detalles de Pedido'

    @property
    def subtotal(self):
        """Subtotal = cantidad * precio_unitario."""
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f'{self.cantidad} × {self.material.nombre}'

    def save(self, *args, **kwargs):
        """
        Al crear almacenamos el precio unitario actual del material
        y recalculamos el total del pedido.
        """
        if not self.pk:
            # Capturar el precio cuando se cree
            self.precio_unitario = self.material.precio
        
        super().save(*args, **kwargs)
        # Recalcular el total en forma atomica
        self.pedido.calcular_total()
