from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('tables', '0010_alter_room_updated_at_alter_table_updated_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='restaurant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tables_room_set',
                to='tenants.restaurant',
                verbose_name='Restoran',
            ),
        ),
    ]
