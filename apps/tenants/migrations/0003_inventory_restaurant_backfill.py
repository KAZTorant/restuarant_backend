from django.db import migrations


ADD_INVENTORY_RESTAURANT_SQL = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'inventory_inventoryitem') THEN
        ALTER TABLE inventory_inventoryitem
            ADD COLUMN IF NOT EXISTS restaurant_id bigint NULL
            REFERENCES tenants_restaurant(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'inventory_inventrycategory') THEN
        ALTER TABLE inventory_inventrycategory
            ADD COLUMN IF NOT EXISTS restaurant_id bigint NULL
            REFERENCES tenants_restaurant(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'inventory_supplier') THEN
        ALTER TABLE inventory_supplier
            ADD COLUMN IF NOT EXISTS restaurant_id bigint NULL
            REFERENCES tenants_restaurant(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'inventory_inventoryrecord') THEN
        ALTER TABLE inventory_inventoryrecord
            ADD COLUMN IF NOT EXISTS restaurant_id bigint NULL
            REFERENCES tenants_restaurant(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;
"""


def backfill_inventory_restaurants(apps, schema_editor):
    Restaurant = apps.get_model('tenants', 'Restaurant')
    default = Restaurant.objects.filter(slug='default').first()
    if not default:
        return

    connection = schema_editor.connection
    tables = (
        'inventory_inventoryitem',
        'inventory_inventrycategory',
        'inventory_supplier',
        'inventory_inventoryrecord',
    )
    for table in tables:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = %s AND column_name = 'restaurant_id'
                """,
                [table],
            )
            if cursor.fetchone():
                cursor.execute(
                    f'UPDATE {table} SET restaurant_id = %s WHERE restaurant_id IS NULL',
                    [default.pk],
                )


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0002_populate_default_restaurant'),
    ]

    operations = [
        migrations.RunSQL(ADD_INVENTORY_RESTAURANT_SQL, migrations.RunSQL.noop),
        migrations.RunPython(backfill_inventory_restaurants, migrations.RunPython.noop),
    ]
