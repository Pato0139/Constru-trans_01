from django.db import migrations


def make_fecha_actualizacion_nullable(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'pago_pedido' AND column_name = 'fecha_actualizacion'
                    ) THEN
                        ALTER TABLE pago_pedido ALTER COLUMN fecha_actualizacion DROP NOT NULL;
                        ALTER TABLE pago_pedido ALTER COLUMN fecha_actualizacion SET DEFAULT NULL;
                    END IF;
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'pago_pedido_pedido_id_uniq'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'pago_pedido_pedido_id_key'
                    ) THEN
                        ALTER TABLE pago_pedido ADD CONSTRAINT pago_pedido_pedido_id_uniq UNIQUE (pedido_id);
                    END IF;
                END $$;
            """)


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0003_drop_legacy_not_null_pago_pedido"),
    ]

    operations = [
        migrations.RunPython(
            make_fecha_actualizacion_nullable,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
