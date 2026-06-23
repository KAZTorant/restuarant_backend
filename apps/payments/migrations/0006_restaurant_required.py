from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0002_populate_default_restaurant'),
        ('payments', '0005_add_restaurant_tenant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentcalculation',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payments_paymentcalculation_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
