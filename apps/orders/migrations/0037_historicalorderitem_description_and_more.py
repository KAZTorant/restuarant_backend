# Generated by Django 5.2 on 2025-04-24 19:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0036_merge_20250424_2359"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalorderitem",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
    ]
