from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('printers', '0007_print_gateway_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='printer',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='printers_printer_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AddField(
            model_name='printgatewaylocation',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='printers_printgatewaylocation_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
