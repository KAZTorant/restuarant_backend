from django.db import models
from django.conf import settings
from django.utils.timezone import now


class OrderItemDeletionLog(models.Model):
    REASON_RETURN = "return"
    REASON_WASTE = "waste"
    REASON_CHOICES = [
        (REASON_RETURN, "Anbara qaytarma"),
        (REASON_WASTE,  "Tullantı")
    ]

    order_id = models.IntegerField(verbose_name="Sifariş ID")
    order_item_id = models.IntegerField(verbose_name="Sifariş Məhsulu ID")
    table_id = models.IntegerField(verbose_name="Stol ID")
    waitress_name = models.CharField(
        max_length=150, verbose_name="Ofisiantın Adı")
    meal_name = models.CharField(max_length=255, verbose_name="Yeməyin Adı")
    quantity = models.DecimalField(
        max_digits=10, decimal_places=3, verbose_name="Miqdar")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Qiymət")
    customer_number = models.PositiveIntegerField(verbose_name="Müştəri №")
    reason = models.CharField(
        max_length=20, choices=REASON_CHOICES, verbose_name="Səbəb"
    )
    comment = models.TextField(blank=True, null=True)

    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_orderitem_logs",
        verbose_name="Silən İstifadəçi"
    )
    deleted_at = models.DateTimeField(
        default=now, verbose_name="Silinmə Vaxtı")

    class Meta:
        verbose_name = "Silinmiş Sifariş Məhsulu"
        verbose_name_plural = "Silinmiş Sifariş Məhsulları"
        indexes = [models.Index(fields=["reason", "deleted_at"])]

    def __str__(self):
        return (
            f"{self.get_reason_display()} | "
            f"Sifariş {self.order_id} / Stol {self.table_id} | "
            f"{self.meal_name} × {self.quantity}"
        )
