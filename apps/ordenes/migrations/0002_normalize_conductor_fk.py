# Generated migration for Conductor FK normalization
# Changes conductor FK from Usuario to Conductor in Pedido and Entrega

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ordenes', '0001_initial'),
        ('usuarios', '0003_rol_usuario_rol'),
    ]

    operations = [
        # Alter Pedido.conductor to point to Conductor instead of Usuario
        migrations.AlterField(
            model_name='pedido',
            name='conductor',
            field=models.ForeignKey(
                null=True, 
                blank=True, 
                on_delete=django.db.models.deletion.SET_NULL, 
                related_name='pedidos_asignados', 
                to='usuarios.conductor'
            ),
        ),
        # Alter Entrega.conductor to point to Conductor instead of Usuario
        migrations.AlterField(
            model_name='entrega',
            name='conductor',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, 
                related_name='entregas_asignadas', 
                to='usuarios.conductor'
            ),
        ),
        # Add constraints to Pedido
        migrations.AddConstraint(
            model_name='pedido',
            constraint=models.CheckConstraint(
                check=models.Q(total__gte=0),
                name='chk_pedido_total_gte_0'
            ),
        ),
        migrations.AddConstraint(
            model_name='pedido',
            constraint=models.CheckConstraint(
                check=models.Q(precio__gte=0),
                name='chk_pedido_precio_gte_0'
            ),
        ),
        # Add constraints to DetallePedido
        migrations.AddConstraint(
            model_name='detallepedido',
            constraint=models.CheckConstraint(
                check=models.Q(cantidad__gt=0),
                name='chk_detalle_pedido_cantidad_gt_0'
            ),
        ),
        migrations.AddConstraint(
            model_name='detallepedido',
            constraint=models.CheckConstraint(
                check=models.Q(precio_unitario__gte=0),
                name='chk_detalle_pedido_precio_unitario_gte_0'
            ),
        ),
        migrations.AddConstraint(
            model_name='detallepedido',
            constraint=models.UniqueConstraint(
                fields=['pedido', 'material'],
                name='uq_detalle_pedido_pedido_material'
            ),
        ),
    ]
