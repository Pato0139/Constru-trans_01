from django.db import migrations


def make_legacy_columns_nullable(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pago_pedido' AND column_name = 'metodo_pago_legacy') THEN
                        ALTER TABLE pago_pedido ALTER COLUMN metodo_pago_legacy DROP NOT NULL;
                        ALTER TABLE pago_pedido ALTER COLUMN metodo_pago_legacy SET DEFAULT NULL;
                    END IF;
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pago_pedido' AND column_name = 'referencia') THEN
                        ALTER TABLE pago_pedido ALTER COLUMN referencia DROP NOT NULL;
                        ALTER TABLE pago_pedido ALTER COLUMN referencia SET DEFAULT NULL;
                    END IF;
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pago_pedido' AND column_name = 'historial') THEN
                        ALTER TABLE pago_pedido ALTER COLUMN historial DROP NOT NULL;
                        ALTER TABLE pago_pedido ALTER COLUMN historial SET DEFAULT '{}'::jsonb;
                    END IF;
                END $$;
            """)


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0002_alter_detallepago_concepto_alter_factura_impuestos_and_more"),
    ]

    operations = [
        migrations.RunPython(make_legacy_columns_nullable, reverse_code=migrations.RunPython.noop),
    ]
