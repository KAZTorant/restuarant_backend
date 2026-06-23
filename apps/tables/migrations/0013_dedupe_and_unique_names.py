from django.db import migrations, models
from django.db.models import Q
from django.db.models.functions import Lower


def dedupe_names(apps, schema_editor):
    Room = apps.get_model('tables', 'Room')
    seen = {}
    for room in Room.objects.order_by('restaurant_id', 'name', 'pk'):
        key = (room.restaurant_id, room.name.lower())
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count > 1:
            room.name = f"{room.name} ({count})"
            room.save(update_fields=['name'])

    Table = apps.get_model('tables', 'Table')
    seen = {}
    for table in Table.objects.exclude(
        Q(number__isnull=True) | Q(number=''),
    ).order_by('room_id', 'number', 'pk'):
        key = (table.room_id, table.number.lower())
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count > 1:
            table.number = f"{table.number} ({count})"
            table.save(update_fields=['number'])


class Migration(migrations.Migration):

    dependencies = [
        ('tables', '0012_restaurant_required'),
    ]

    operations = [
        migrations.RunPython(dedupe_names, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='room',
            constraint=models.UniqueConstraint(
                Lower('name'),
                'restaurant',
                name='unique_room_name_ci_per_restaurant',
            ),
        ),
        migrations.AddConstraint(
            model_name='table',
            constraint=models.UniqueConstraint(
                Lower('number'),
                'room',
                condition=Q(number__isnull=False) & ~Q(number=''),
                name='unique_table_number_ci_per_room',
            ),
        ),
    ]
