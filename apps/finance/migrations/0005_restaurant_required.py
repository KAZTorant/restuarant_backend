from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0002_populate_default_restaurant'),
        ('finance', '0004_add_restaurant_tenant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='income',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='finance_income_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AlterField(
            model_name='expense',
            name='restaurant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='finance_expense_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
