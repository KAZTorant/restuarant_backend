from django.db import models
from django.utils import timezone

from apps.commons.models import TenantModel
from apps.users.models.whatsapp_message import normalize_whatsapp_phone


class WhatsAppSession(TenantModel, models.Model):
    """Sender WhatsApp account linked to one restaurant."""

    phone = models.CharField(max_length=20, blank=True, verbose_name='Qoşulmuş nömrə')
    connected_at = models.DateTimeField(null=True, blank=True, verbose_name='Qoşulma vaxtı')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Yeniləndi')

    class Meta:
        verbose_name = 'WhatsApp sessiyası'
        verbose_name_plural = 'WhatsApp sessiyaları'
        constraints = [
            models.UniqueConstraint(
                fields=['restaurant'],
                name='unique_restaurant_whatsapp_session',
            ),
        ]

    def __str__(self):
        return self.phone or 'Qoşulmayıb'


def touch_whatsapp_session(restaurant, phone='', logout=False):
    if logout:
        WhatsAppSession.objects.filter(restaurant=restaurant).update(phone='')
        return
    digits = normalize_whatsapp_phone(phone)
    if not digits:
        return
    session, created = WhatsAppSession.objects.get_or_create(
        restaurant=restaurant,
        defaults={'phone': digits, 'connected_at': timezone.now()},
    )
    if created:
        return
    session.phone = digits
    if not session.connected_at:
        session.connected_at = timezone.now()
    session.save(update_fields=['phone', 'connected_at', 'updated_at'])
