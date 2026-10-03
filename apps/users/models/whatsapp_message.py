from django.db import IntegrityError, models, transaction
from django.utils import timezone

from apps.commons.models import TenantModel


def normalize_whatsapp_phone(phone):
    digits = ''.join(ch for ch in str(phone or '') if ch.isdigit())
    if digits.startswith('0'):
        digits = digits[1:]
    if digits and not digits.startswith('994') and len(digits) < 12:
        digits = '994' + digits
    return digits


def _ack_rank(ack):
    if ack is None:
        return -2
    if ack < 0:
        return -1
    return ack


class WhatsAppMessage(TenantModel, models.Model):
    """Outgoing WhatsApp message and the delivery state WhatsApp reports back."""

    KIND_ORDER_DELETION = 'order_deletion'
    KIND_TEXT = 'text'
    KIND_INTAKE_REPLY = 'intake_reply'
    KIND_CHOICES = (
        (KIND_ORDER_DELETION, 'Sifariş silinməsi'),
        (KIND_TEXT, 'Mesaj'),
        (KIND_INTAKE_REPLY, 'Anbar cavabı'),
    )

    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_DELIVERED = 'delivered'
    STATUS_READ = 'read'
    STATUS_PLAYED = 'played'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Gözləyir'),
        (STATUS_SENT, 'Serverə çatdı'),
        (STATUS_DELIVERED, 'Çatdı'),
        (STATUS_READ, 'Oxundu'),
        (STATUS_PLAYED, 'Oxundu (səs)'),
        (STATUS_FAILED, 'Göndərilmədi'),
    )

    recipient_phone = models.CharField(max_length=20, verbose_name='Alıcı nömrə')
    recipient_name = models.CharField(max_length=100, blank=True, verbose_name='Alıcı')
    from_number = models.CharField(max_length=20, blank=True, verbose_name='Göndərən nömrə')
    body = models.TextField(blank=True, verbose_name='Mesaj')
    kind = models.CharField(
        max_length=32,
        choices=KIND_CHOICES,
        default=KIND_TEXT,
        verbose_name='Növ',
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='Status',
    )
    last_ack = models.SmallIntegerField(null=True, blank=True, verbose_name='WhatsApp ack')
    wa_message_id = models.CharField(max_length=128, blank=True, verbose_name='WhatsApp mesaj ID')
    order_id = models.PositiveBigIntegerField(null=True, blank=True, verbose_name='Sifariş')
    error = models.TextField(blank=True, verbose_name='Xəta')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Göndərildi')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='Çatdı')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='Oxundu')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaradıldı')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Yeniləndi')

    class Meta:
        verbose_name = 'WhatsApp mesajı'
        verbose_name_plural = 'WhatsApp mesajları'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['restaurant', 'wa_message_id'],
                condition=~models.Q(wa_message_id=''),
                name='unique_restaurant_wa_message',
            ),
        ]
        indexes = [
            models.Index(fields=['restaurant', '-created_at'], name='users_wa_msg_rest_created'),
        ]

    def __str__(self):
        return f'{self.recipient_phone} · {self.get_status_display()}'

    def apply_ack(self, ack):
        try:
            ack = int(ack)
        except (TypeError, ValueError):
            return
        if self.last_ack is not None and _ack_rank(self.last_ack) > _ack_rank(ack):
            return
        self.last_ack = ack
        now = timezone.now()
        if ack < 0:
            self.status = self.STATUS_FAILED
            return
        if ack == 0:
            if self.status in ('', self.STATUS_FAILED):
                self.status = self.STATUS_PENDING
            return
        self.error = ''
        if ack >= 1:
            self.status = self.STATUS_SENT
            if not self.sent_at:
                self.sent_at = now
        if ack >= 2:
            self.status = self.STATUS_DELIVERED
            if not self.delivered_at:
                self.delivered_at = now
        if ack >= 3:
            self.status = self.STATUS_READ
            if not self.read_at:
                self.read_at = now
        if ack >= 4:
            self.status = self.STATUS_PLAYED
            if not self.read_at:
                self.read_at = now


def _optional_int(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def record_whatsapp_delivery(
    *,
    restaurant,
    django_message_id=None,
    wa_message_id='',
    ack=None,
    recipient_phone='',
    recipient_name='',
    body='',
    kind='',
    from_number='',
    error='',
    order_id=None,
):
    """Create or update one outgoing message. Later acks never downgrade status."""
    wa_message_id = (wa_message_id or '')[:128]
    django_message_id = _optional_int(django_message_id)
    order_id = _optional_int(order_id)
    with transaction.atomic():
        message = None
        if django_message_id:
            message = (
                WhatsAppMessage.objects.select_for_update()
                .filter(pk=django_message_id, restaurant=restaurant)
                .first()
            )
        if message is None and wa_message_id:
            message = (
                WhatsAppMessage.objects.select_for_update()
                .filter(restaurant=restaurant, wa_message_id=wa_message_id)
                .first()
            )
        if message is None and not (body or '').strip():
            return None
        if message is None:
            message = WhatsAppMessage(
                restaurant=restaurant,
                recipient_phone=normalize_whatsapp_phone(recipient_phone),
                recipient_name=recipient_name or '',
                body=body or '',
                kind=kind or WhatsAppMessage.KIND_TEXT,
                from_number=normalize_whatsapp_phone(from_number),
                wa_message_id=wa_message_id,
                order_id=order_id,
            )
            if ack is not None:
                message.apply_ack(ack)
            if error and message.status == WhatsAppMessage.STATUS_FAILED:
                message.error = error
            elif error and ack is None:
                message.status = WhatsAppMessage.STATUS_FAILED
                message.error = error
            try:
                message.save()
            except IntegrityError:
                existing = (
                    WhatsAppMessage.objects.select_for_update()
                    .filter(restaurant=restaurant, wa_message_id=wa_message_id)
                    .first()
                )
                if existing is None:
                    raise
                message = existing
                if ack is not None:
                    message.apply_ack(ack)
                if from_number and not message.from_number:
                    message.from_number = normalize_whatsapp_phone(from_number)
                message.save()
            return message

        if wa_message_id and not message.wa_message_id:
            message.wa_message_id = wa_message_id
        if from_number and not message.from_number:
            message.from_number = normalize_whatsapp_phone(from_number)
        if body and not message.body:
            message.body = body
        if recipient_phone and not message.recipient_phone:
            message.recipient_phone = normalize_whatsapp_phone(recipient_phone)
        if recipient_name and not message.recipient_name:
            message.recipient_name = recipient_name
        if order_id and not message.order_id:
            message.order_id = order_id
        if ack is not None:
            message.apply_ack(ack)
        if error and message.status == WhatsAppMessage.STATUS_FAILED and not message.error:
            message.error = error
        elif error and message.status == WhatsAppMessage.STATUS_FAILED:
            message.error = error
        message.save()
        return message
