# Generated by Django 4.2.15 on 2025-04-13 09:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("printers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PreparationPlace",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Hazırlanma yerinin adı",
                        max_length=100,
                        verbose_name="Hazırlanma Yeri Adı",
                    ),
                ),
                (
                    "printer",
                    models.ForeignKey(
                        blank=True,
                        help_text="Bu hazırlıq yerinə təyin edilmiş çap cihazı",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="printers.printer",
                        verbose_name="Çap Cihazı",
                    ),
                ),
            ],
            options={
                "verbose_name": "Hazırlanma Yeri",
                "verbose_name_plural": "Hazırlanma Yerləri",
                "ordering": ["name"],
            },
        ),
    ]
