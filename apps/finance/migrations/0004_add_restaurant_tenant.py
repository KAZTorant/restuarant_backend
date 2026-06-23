from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('finance', '0003_alter_expense_options_alter_income_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='income',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='finance_income_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AddField(
            model_name='expense',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='finance_expense_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
