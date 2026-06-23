import secrets

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.commons.models import TenantModel


class PrintGatewayLocation(TenantModel, models.Model):
    name = models.CharField(_('Location name'), max_length=100)
    token = models.CharField(
        _('Gateway token'),
        max_length=64,
        unique=True,
        editable=False,
        help_text=_('Configure this token in the Print Gateway setup panel.'),
    )
    is_online = models.BooleanField(_('Online'), default=False)
    last_seen_at = models.DateTimeField(_('Last seen'), null=True, blank=True)
    printers_status = models.JSONField(
        _('Printers status'),
        default=dict,
        blank=True,
    )

    class Meta:
        verbose_name = _('Print gateway location')
        verbose_name_plural = _('Print gateway locations')

    def __str__(self):
        status = 'online' if self.is_online else 'offline'
        return f'{self.name} (id={self.pk}, {status})'

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def mark_online(self, printers_status=None):
        self.is_online = True
        self.last_seen_at = timezone.now()
        if printers_status is not None:
            self.printers_status = printers_status
        self.save(update_fields=['is_online', 'last_seen_at', 'printers_status'])

    def mark_offline(self):
        self.is_online = False
        self.last_seen_at = timezone.now()
        self.save(update_fields=['is_online', 'last_seen_at'])
