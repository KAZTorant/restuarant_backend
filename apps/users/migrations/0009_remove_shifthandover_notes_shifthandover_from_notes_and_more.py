# Generated by Django 5.2 on 2025-04-15 07:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0008_shifthandover"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="shifthandover",
            name="notes",
        ),
        migrations.AddField(
            model_name="shifthandover",
            name="from_notes",
            field=models.TextField(blank=True, verbose_name="Göndərən Qeydləri"),
        ),
        migrations.AddField(
            model_name="shifthandover",
            name="to_notes",
            field=models.TextField(blank=True, verbose_name="Qəbul edən Qeydləri"),
        ),
    ]
