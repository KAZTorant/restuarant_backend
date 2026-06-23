from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0002_populate_default_restaurant'),
        ('printers', '0008_add_restaurant_tenant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='printer',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='printers_printer_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AlterField(
            model_name='printgatewaylocation',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='printers_printgatewaylocation_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
