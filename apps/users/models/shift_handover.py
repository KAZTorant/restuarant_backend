from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

User = settings.AUTH_USER_MODEL


class ShiftHandover(models.Model):
    from_user = models.ForeignKey(
        User,
        related_name='shift_handover_from',
        on_delete=models.CASCADE,
        verbose_name="Təhvil verən",
        limit_choices_to={'type': 'admin'}
    )
    to_user = models.ForeignKey(
        User,
        related_name='shift_handover_to',
        on_delete=models.CASCADE,
        verbose_name="Təhvil alan",
        limit_choices_to={'type': 'admin'}

    )
    shift_start = models.DateTimeField(verbose_name="Növbənin Başlanğıcı")
    shift_end = models.DateTimeField(verbose_name="Növbənin Sonu")
    cash_in_kassa = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Kassadakı Məbləğ")
    expected_cash = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Gözlənilən Məbləğ")
    discrepancy = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Uyğunluq Fərqi")
    from_notes = models.TextField(
        blank=True, verbose_name="Təhvil verənin qeydləri")
    to_notes = models.TextField(
        blank=True, verbose_name="Təhvil alanın qeydləri")
    is_confirmed = models.BooleanField(
        default=False, verbose_name="Təsdiqləndi?")
    confirmed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Təsdiqlənmə Vaxtı")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Yaradılma Tarixi")

    class Meta:
        verbose_name = "Növbə Təslimi"
        verbose_name_plural = "Növbə Təslimləri"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.shift_end.date()})"

    def clean(self):
        if self.shift_end < self.shift_start:
            raise ValidationError(
                "Növbənin sonu başlanğıcdan sonra olmalıdır.")
        # Auto-compute discrepancy if expected_cash is set
        if self.expected_cash is not None:
            self.discrepancy = self.cash_in_kassa - self.expected_cash
