from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0002_populate_default_restaurant'),
        ('meals', '0014_add_restaurant_tenant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mealgroup',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='meals_mealgroup_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
