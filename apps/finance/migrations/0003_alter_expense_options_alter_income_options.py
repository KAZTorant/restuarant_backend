# Generated by Django 4.2.15 on 2025-04-08 15:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0002_expense_description_income_description"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="expense",
            options={"verbose_name": "Xərc", "verbose_name_plural": "Xərclər"},
        ),
        migrations.AlterModelOptions(
            name="income",
            options={"verbose_name": "Gəlir", "verbose_name_plural": "Gəlirlər"},
        ),
    ]
