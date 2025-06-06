# Generated by Django 5.2 on 2025-04-16 10:07

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("orders", "0031_historicalorderitem_confirmed_orderitem_confirmed"),
        ("tables", "0009_alter_room_created_at_alter_table_created_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
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
                    "total_price",
                    models.DecimalField(
                        decimal_places=2, max_digits=10, verbose_name="Ümumi məbləğ"
                    ),
                ),
                (
                    "discount_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=10,
                        verbose_name="Endirim",
                    ),
                ),
                (
                    "discount_comment",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Endirim səbəbi"
                    ),
                ),
                (
                    "final_price",
                    models.DecimalField(
                        decimal_places=2, max_digits=10, verbose_name="Son məbləğ"
                    ),
                ),
                (
                    "paid_amount",
                    models.DecimalField(
                        decimal_places=2, max_digits=10, verbose_name="Ödənilən məbləğ"
                    ),
                ),
                (
                    "change",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=10,
                        verbose_name="Qaytarılacaq məbləğ",
                    ),
                ),
                (
                    "payment_type",
                    models.CharField(
                        choices=[
                            ("cash", "Nağd"),
                            ("card", "Kart"),
                            ("other", "Digər"),
                        ],
                        max_length=20,
                        verbose_name="Ödəniş növü",
                    ),
                ),
                (
                    "paid_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Ödəmə tarixi"
                    ),
                ),
                (
                    "orders",
                    models.ManyToManyField(
                        to="orders.order", verbose_name="Sifarişlər"
                    ),
                ),
                (
                    "paid_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Operator",
                    ),
                ),
                (
                    "table",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="tables.table",
                        verbose_name="Masa",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ödəmə",
                "verbose_name_plural": "Ödəmələr",
            },
        ),
    ]
