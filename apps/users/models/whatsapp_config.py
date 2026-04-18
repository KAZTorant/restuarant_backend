from django.db import models


class WhatsAppConfig(models.Model):
    """
    WhatsApp notification configuration.
    Stores owner phone numbers for notifications.
    """
    phone = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Telefon nömrəsi",
        help_text="Format: 994XXXXXXXXX (ölkə kodu ilə birlikdə)"
    )
    name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ad/Qeyd",
        help_text="Nömrə sahibinin adı və ya qeydi (məsələn: 'Rəsmi sahibi', 'Müdir')"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktiv",
        help_text="Deaktiv nömrələrə bildiriş göndərilməyəcək"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Əlavə edilmə tarixi"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yenilənmə tarixi"
    )

    class Meta:
        verbose_name = "WhatsApp Konfiqurasiyası"
        verbose_name_plural = "WhatsApp Konfiqurasiyaları"
        ordering = ['-is_active', 'created_at']

    def __str__(self):
        status = "✓" if self.is_active else "✗"
        name_part = f" ({self.name})" if self.name else ""
        return f"{status} {self.phone}{name_part}"
