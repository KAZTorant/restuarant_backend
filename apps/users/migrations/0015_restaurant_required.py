from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0002_populate_default_restaurant'),
        ('users', '0014_add_restaurant_tenant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shifthandover',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='users_shifthandover_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AlterField(
            model_name='whatsappconfig',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='users_whatsappconfig_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AddConstraint(
            model_name='whatsappconfig',
            constraint=models.UniqueConstraint(
                fields=('restaurant', 'phone'),
                name='unique_restaurant_whatsapp_phone',
            ),
        ),
    ]
