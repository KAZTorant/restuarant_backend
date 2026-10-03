"""
WhatsApp Notification Utility
Communicates with the WhatsApp Web service to send notifications
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    """
    Handles WhatsApp notifications via the WhatsApp Web service
    """
    
    def __init__(self):
        self.service_url = getattr(
            settings, 'WHATSAPP_SERVICE_URL', 'http://localhost:3001'
        ).rstrip('/')
        self.timeout = 20
        self.health_timeout = 5

    def _headers(self):
        key = getattr(settings, 'WHATSAPP_API_KEY', '') or ''
        if key:
            return {'X-API-Key': key}
        return {}
    
    def _normalize_phone(self, phone):
        digits = ''.join(ch for ch in str(phone) if ch.isdigit())
        if digits.startswith('0'):
            digits = digits[1:]
        if not digits.startswith('994') and len(digits) < 12:
            digits = '994' + digits
        return digits

    def _get_owner_phones(self, restaurant=None):
        """
        Get active owner phone numbers from database.
        Falls back to settings.RESTAURANT_OWNER_PHONE if DB is empty.
        
        Returns:
            list: List of active phone numbers
        """
        try:
            # Import here to avoid circular dependency
            from apps.users.models import WhatsAppConfig

            queryset = WhatsAppConfig.objects.filter(is_active=True)
            if restaurant is not None:
                queryset = queryset.filter(restaurant=restaurant)
            raw_phones = list(queryset.values_list('phone', flat=True).order_by('created_at'))
            phones = []
            seen = set()
            for phone in raw_phones:
                normalized = self._normalize_phone(phone)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                phones.append(normalized)
            
            if phones:
                logger.info(
                    "WA recipients restaurant=%s count=%s phones=%s raw=%s",
                    getattr(restaurant, 'pk', None),
                    len(phones),
                    phones,
                    raw_phones,
                )
                return phones
            logger.warning(
                "No active WhatsApp phones for restaurant=%s",
                getattr(restaurant, 'pk', None),
            )
        except Exception as e:
            logger.warning("Could not load WhatsApp phones from database: %s", e)

        return []
    
    def _session_status(self, restaurant):
        slug = getattr(restaurant, 'slug', None)
        if not slug:
            return {'ready': False, 'error': 'restaurant missing'}
        url = f"{self.service_url}/status"
        try:
            response = requests.get(
                url,
                params={'restaurant': slug},
                headers=self._headers(),
                timeout=self.health_timeout,
            )
            if response.status_code == 200:
                return response.json()
            logger.error("WA status_failed restaurant=%s code=%s", slug, response.status_code)
            return {'ready': False, 'error': f'status {response.status_code}'}
        except requests.exceptions.RequestException as exc:
            logger.error("WA status_error restaurant=%s error=%s", slug, exc)
            return {'ready': False, 'error': str(exc)}

    def is_configured(self, restaurant=None):
        """Recipient list exists and this restaurant's own WhatsApp session is ready."""
        if restaurant is None or not self._get_owner_phones(restaurant):
            logger.warning("Restaurant owner phone(s) not configured")
            return False
        return bool(self._session_status(restaurant).get('ready'))
    
    def get_status(self):
        """Get WhatsApp service status"""
        url = f"{self.service_url}/health"
        try:
            logger.info(f"Getting WhatsApp service status from: {url}")
            response = requests.get(url, headers=self._headers(), timeout=self.health_timeout)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"WhatsApp status retrieved successfully: {data}")
                return {
                    'ready': data.get('whatsapp_ready', False),
                    'authenticated': data.get('whatsapp_ready', False),
                }
            else:
                error_msg = f"Service returned status {response.status_code}"
                logger.error(
                    f"WhatsApp service status check failed.\n"
                    f"  URL: {url}\n"
                    f"  Status Code: {response.status_code}\n"
                    f"  Response: {response.text[:500]}"
                )
                return {'ready': False, 'error': error_msg}
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout after {self.health_timeout}s"
            logger.error(f"WhatsApp service timeout. URL: {url}, Error: {e}")
            return {'ready': False, 'error': error_msg}
        except requests.exceptions.ConnectionError as e:
            error_msg = "Connection refused or service not running"
            logger.error(f"WhatsApp service connection failed. URL: {url}, Error: {e}")
            return {'ready': False, 'error': error_msg}
        except requests.exceptions.RequestException as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"WhatsApp service request error. URL: {url}, Error: {error_msg}")
            return {'ready': False, 'error': error_msg}
    
    def _recipient_name(self, restaurant, phone):
        from apps.users.models import WhatsAppConfig

        normalized = self._normalize_phone(phone)
        if restaurant is None or not normalized:
            return ''
        for config in WhatsAppConfig.objects.filter(restaurant=restaurant):
            if self._normalize_phone(config.phone) == normalized:
                return config.name or ''
        return ''

    def _deletion_message(self, order_item_info, restaurant):
        comment = order_item_info.get('comment') or ''
        restaurant_name = getattr(restaurant, 'name', None) or 'N/A'
        message = '🚨 *SİFARİŞ MƏHSUL SİLİNDİ*\n\n'
        message += f'🏪 *Restoran:* {restaurant_name}\n'
        message += f"👤 *Admin:* {order_item_info.get('admin_name') or 'N/A'}\n"
        message += f"🏠 *Zal:* {order_item_info.get('room_name') or 'N/A'}\n"
        message += f"🍽️ *Masa:* {order_item_info.get('table_number') or 'N/A'}\n"
        message += f"🆔 *Sifariş:* #{order_item_info.get('order_id') or 'N/A'}\n\n"
        message += f"📦 *Məhsul:* {order_item_info.get('meal_name') or 'N/A'}\n"
        message += f"🔢 *Miqdar:* {order_item_info.get('quantity') or 0}\n"
        message += f"💰 *Qiymət:* {order_item_info.get('price') or 0} AZN\n\n"
        message += f"📋 *Səbəb:* {order_item_info.get('reason_display') or 'N/A'}\n\n"
        message += f"⏰ *Sifariş vaxtı:* {order_item_info.get('order_created_at') or 'N/A'}\n"
        message += f"🗑️ *Silinmə vaxtı:* {order_item_info.get('deleted_at') or 'N/A'}"
        if comment:
            message += f'\n\n💬 *Qeyd:* {comment}'
        return message

    def _open_message(self, restaurant, phone, body, kind, order_id=None, error=''):
        from apps.users.models import WhatsAppMessage
        from apps.users.models.whatsapp_message import record_whatsapp_delivery

        if restaurant is None:
            logger.warning('WA message_skipped reason=no_restaurant phone=%s', phone)
            return None
        message = record_whatsapp_delivery(
            restaurant=restaurant,
            recipient_phone=self._normalize_phone(phone),
            recipient_name=self._recipient_name(restaurant, phone),
            body=body,
            kind=kind,
            order_id=order_id,
            error=error,
            ack=-1 if error else None,
        )
        if error and message.status != WhatsAppMessage.STATUS_FAILED:
            message.status = WhatsAppMessage.STATUS_FAILED
            message.error = error
            message.save(update_fields=['status', 'error', 'updated_at'])
        return message

    def _finish_message(self, message, data=None, error=''):
        from apps.users.models.whatsapp_message import record_whatsapp_delivery
        from apps.users.models.whatsapp_session import touch_whatsapp_session

        if message is None:
            return
        data = data or {}
        ack = data.get('ack')
        if error:
            ack = -1
        elif data.get('success'):
            try:
                ack_value = int(ack) if ack is not None else 0
            except (TypeError, ValueError):
                ack_value = 0
            if ack_value < 1:
                ack = 1
        record_whatsapp_delivery(
            restaurant=message.restaurant,
            django_message_id=message.pk,
            wa_message_id=data.get('wa_message_id') or '',
            ack=ack,
            from_number=data.get('from_number') or '',
            error=error or data.get('error') or data.get('details') or '',
        )
        from_number = data.get('from_number') or ''
        if from_number:
            touch_whatsapp_session(message.restaurant, phone=from_number)

    def send_message(self, phone, message, restaurant=None, kind=None, order_id=None):
        """
        Send a WhatsApp message from this restaurant's own logged-in number.
        """
        from apps.users.models import WhatsAppMessage

        kind = kind or WhatsAppMessage.KIND_TEXT
        if restaurant is None:
            logger.warning('WA send_skipped reason=no_restaurant phone=%s', phone)
            return False

        record = self._open_message(restaurant, phone, message, kind, order_id=order_id)
        url = f"{self.service_url}/send-message"
        payload = {
            'restaurant': restaurant.slug,
            'phone': phone,
            'message': message,
            'django_message_id': record.pk if record else None,
            'kind': kind,
            'order_id': order_id,
        }
        try:
            logger.info(
                'WA send_start restaurant=%s phone=%s',
                restaurant.slug,
                self._normalize_phone(phone),
            )
            response = requests.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
            data = {}
            try:
                data = response.json()
            except ValueError:
                data = {}
            if response.status_code == 200 and data.get('success'):
                self._finish_message(record, data)
                logger.info('WA send_ok restaurant=%s phone=%s', restaurant.slug, phone)
                return True
            error = data.get('error') or data.get('details') or f'HTTP {response.status_code}'
            self._finish_message(record, data, error=error)
            logger.error('WA send_failed restaurant=%s phone=%s error=%s', restaurant.slug, phone, error)
            return False
        except requests.exceptions.RequestException as exc:
            self._finish_message(record, error=str(exc))
            logger.error('WA send_error restaurant=%s phone=%s error=%s', restaurant.slug, phone, exc)
            return False

    def notify_order_item_deleted(self, order_item_info, restaurant=None):
        """
        Send notification to restaurant owner(s) when an order item is deleted
        If multiple owner phones configured, sends to all.
        
        Args:
            order_item_info (dict): Dictionary containing order item details
                - admin_name: Name of admin who deleted the item
                - room_name: Room/hall name
                - table_number: Table number
                - order_id: Order ID
                - order_created_at: When the order was created
                - deleted_at: When the item was deleted
                - meal_name: Name of the meal
                - quantity: Quantity deleted
                - price: Price of deleted item(s)
                - reason: Reason for deletion (return/waste)
                - reason_display: Display text for reason
                - comment: Additional comment
        """
        from apps.users.models import WhatsAppMessage

        if restaurant is None:
            logger.warning('WA notify_skipped reason=no_restaurant')
            return False

        owner_phones = self._get_owner_phones(restaurant)
        if not owner_phones:
            logger.warning(
                'WA notify_skipped restaurant=%s reason=no_recipients',
                restaurant.slug,
            )
            return False

        body = self._deletion_message(order_item_info, restaurant)
        order_id = order_item_info.get('order_id')
        try:
            order_id = int(order_id)
        except (TypeError, ValueError):
            order_id = None

        success_count = 0
        for owner_phone in owner_phones:
            sent = self.send_message(
                owner_phone,
                body,
                restaurant=restaurant,
                kind=WhatsAppMessage.KIND_ORDER_DELETION,
                order_id=order_id,
            )
            if sent:
                success_count += 1

        logger.info(
            'WA notify_result restaurant=%s sent=%s total=%s',
            restaurant.slug,
            success_count,
            len(owner_phones),
        )
        return success_count > 0


# Singleton instance
_whatsapp_notifier = None


def get_whatsapp_notifier():
    """Get or create WhatsApp notifier singleton instance"""
    global _whatsapp_notifier
    if _whatsapp_notifier is None:
        _whatsapp_notifier = WhatsAppNotifier()
    return _whatsapp_notifier
