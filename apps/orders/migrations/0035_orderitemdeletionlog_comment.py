# Generated by Django 5.2 on 2025-04-23 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0034_orderitemdeletionlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitemdeletionlog",
            name="comment",
            field=models.TextField(blank=True, null=True),
        ),
    ]
