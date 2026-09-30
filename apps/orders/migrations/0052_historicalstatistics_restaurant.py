from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('orders', '0051_restaurant_required'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalstatistics',
            name='restaurant',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
