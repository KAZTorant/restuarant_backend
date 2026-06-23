from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0002_populate_default_restaurant'),
        ('orders', '0050_add_restaurant_tenant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workperiodconfig',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='orders_workperiodconfig_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AlterField(
            model_name='statistics',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='orders_statistics_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AlterField(
            model_name='summary',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='orders_summary_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AlterField(
            model_name='report',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='orders_report_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
