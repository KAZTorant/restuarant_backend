from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('meals', '0013_auto_20260210_1817'),
    ]

    operations = [
        migrations.AddField(
            model_name='mealgroup',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='meals_mealgroup_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
