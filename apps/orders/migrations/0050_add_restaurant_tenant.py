from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('orders', '0049_historicalstatistics_initial_card_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='workperiodconfig',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='orders_workperiodconfig_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AddField(
            model_name='statistics',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='orders_statistics_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AddField(
            model_name='summary',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='orders_summary_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AddField(
            model_name='report',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='orders_report_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
