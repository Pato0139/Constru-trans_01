# Generated migration for conductor FK - Usuario to Conductor

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ordenes', '0002_normalize_conductor_fk'),
        ('usuarios', '0006_rol_usuario_rol_sql'),
    ]

    operations = [
        # Clean up invalid conductor references (must be real conductors)
        migrations.RunSQL(
            sql="""
            UPDATE pedido p
            SET conductor_id = NULL
            WHERE conductor_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM conductor c WHERE c.usuario_id = p.conductor_id);
            """,
            reverse_sql="-- No reverse needed"
        ),
        migrations.RunSQL(
            sql="""
            UPDATE entrega e
            SET conductor_id = NULL
            WHERE conductor_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM conductor c WHERE c.usuario_id = e.conductor_id);
            """,
            reverse_sql="-- No reverse needed"
        ),
        # Change FK to reference conductor.usuario_id instead of usuario.id
        migrations.AlterField(
            model_name='pedido',
            name='conductor',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='usuarios.conductor'
            ),
        ),
        migrations.AlterField(
            model_name='entrega',
            name='conductor',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='usuarios.conductor'
            ),
        ),
    ]
