from django.db import models
from apps.printers.models.printer import Printer


class PreparationPlace(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Hazırlanma Yeri Adı",
        help_text="Hazırlanma yerinin adı"
    )
    printer = models.ForeignKey(
        Printer,
        on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name="Çap Cihazı",
        help_text="Bu hazırlıq yerinə təyin edilmiş çap cihazı"
    )

    class Meta:
        verbose_name = "Hazırlanma Yeri"
        verbose_name_plural = "Hazırlanma Yerləri"
        ordering = ['name']

    def __str__(self):
        return self.name
