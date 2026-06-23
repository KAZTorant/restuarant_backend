from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('users', '0013_whatsappconfig'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=150, unique=False),
        ),
        migrations.AddField(
            model_name='user',
            name='restaurant',
            field=models.ForeignKey(
                blank=True,
                help_text='Superuser üçün boş buraxın.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='users',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                condition=models.Q(('restaurant__isnull', False)),
                fields=('restaurant', 'username'),
                name='unique_restaurant_username',
            ),
        ),
        migrations.AddField(
            model_name='shifthandover',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='users_shifthandover_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AddField(
            model_name='whatsappconfig',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='users_whatsappconfig_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
        migrations.AlterField(
            model_name='whatsappconfig',
            name='phone',
            field=models.CharField(
                help_text='Format: 994XXXXXXXXX (ölkə kodu ilə birlikdə)',
                max_length=20,
                verbose_name='Telefon nömrəsi',
            ),
        ),
    ]
