# Generated by Django 5.2 on 2025-04-15 07:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_remove_shifthandover_notes_shifthandover_from_notes_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="shifthandover",
            name="is_overridden",
        ),
        migrations.RemoveField(
            model_name="shifthandover",
            name="overridden_at",
        ),
    ]
