from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('payments', '0004_paymentcalculation'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentcalculation',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payments_paymentcalculation_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
