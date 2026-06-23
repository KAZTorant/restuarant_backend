from django.db import migrations


def create_default_restaurant_and_backfill(apps, schema_editor):
    Restaurant = apps.get_model('tenants', 'Restaurant')
    default, _ = Restaurant.objects.get_or_create(
        slug='default',
        defaults={
            'name': 'Default Restoran',
            'is_active': True,
        },
    )

    tenant_models = [
        ('users', 'ShiftHandover'),
        ('users', 'WhatsAppConfig'),
        ('tables', 'Room'),
        ('meals', 'MealGroup'),
        ('printers', 'Printer'),
        ('printers', 'PrintGatewayLocation'),
        ('finance', 'Income'),
        ('finance', 'Expense'),
        ('orders', 'WorkPeriodConfig'),
        ('orders', 'Statistics'),
        ('orders', 'Summary'),
        ('orders', 'Report'),
        ('payments', 'PaymentCalculation'),
    ]

    User = apps.get_model('users', 'User')
    User.objects.filter(restaurant__isnull=True, is_superuser=False).update(restaurant=default)

    for app_label, model_name in tenant_models:
        model = apps.get_model(app_label, model_name)
        model.objects.filter(restaurant__isnull=True).update(restaurant=default)


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('users', '0014_add_restaurant_tenant'),
        ('tables', '0011_add_restaurant_tenant'),
        ('meals', '0014_add_restaurant_tenant'),
        ('printers', '0008_add_restaurant_tenant'),
        ('finance', '0004_add_restaurant_tenant'),
        ('orders', '0050_add_restaurant_tenant'),
        ('payments', '0005_add_restaurant_tenant'),
    ]

    operations = [
        migrations.RunPython(
            create_default_restaurant_and_backfill,
            migrations.RunPython.noop,
        ),
    ]
