# Generated migration for material.catalogo_id NOT NULL and user names cleanup

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0007_comprehensive_checks'),
    ]

    operations = [
        # Fill NULL catalogo_id with a default (safety step)
        migrations.RunSQL(
            sql="""
            UPDATE material_construccion 
            SET catalogo_id = (SELECT codigo_catalogo FROM catalogo LIMIT 1)
            WHERE catalogo_id IS NULL;
            """,
            reverse_sql="-- Reverse would require logging deleted data"
        ),
        
        # Make catalogo_id NOT NULL
        migrations.AlterField(
            model_name='materialconstruccion',
            name='catalogo',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='materiales',
                to='usuarios.catalogo'
            ),
        ),
        
        # Consolidate nombres/apellidos from first_name/last_name
        migrations.RunSQL(
            sql="""
            UPDATE usuario 
            SET nombres = COALESCE(NULLIF(nombres, ''), first_name, 'N/A')
            WHERE (nombres IS NULL OR nombres = '') AND first_name IS NOT NULL;
            
            UPDATE usuario 
            SET apellidos = COALESCE(NULLIF(apellidos, ''), last_name, 'N/A')
            WHERE (apellidos IS NULL OR apellidos = '') AND last_name IS NOT NULL;
            """,
            reverse_sql="-- No reverse needed"
        ),
        
        # Remove Django legacy fields (optional - safer to keep for compatibility)
        # migrations.RemoveField(
        #     model_name='usuario',
        #     name='first_name',
        # ),
        # migrations.RemoveField(
        #     model_name='usuario',
        #     name='last_name',
        # ),
    ]
