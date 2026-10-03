import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import Restaurant
from apps.users.models.whatsapp_message import record_whatsapp_delivery
from apps.users.models.whatsapp_session import touch_whatsapp_session

logger = logging.getLogger(__name__)


class WhatsAppDeliveryView(APIView):
    """WhatsApp service reports session login and message ack updates."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        expected = getattr(settings, 'WHATSAPP_API_KEY', '') or ''
        provided = request.headers.get('X-API-Key', '')
        if not expected or provided != expected:
            return Response({'ok': False}, status=status.HTTP_401_UNAUTHORIZED)

        slug = str(request.data.get('restaurant') or '').strip()
        restaurant = Restaurant.objects.filter(slug=slug, is_active=True).first()
        if restaurant is None:
            return Response({'ok': False, 'error': 'restaurant'}, status=status.HTTP_400_BAD_REQUEST)

        event = request.data.get('event') or 'message'
        if event == 'session':
            touch_whatsapp_session(
                restaurant,
                phone=request.data.get('from_number') or '',
                logout=bool(request.data.get('logout')),
            )
            logger.info('WA session_update restaurant=%s logout=%s', slug, bool(request.data.get('logout')))
            return Response({'ok': True})

        message = record_whatsapp_delivery(
            restaurant=restaurant,
            django_message_id=request.data.get('django_message_id') or None,
            wa_message_id=request.data.get('wa_message_id') or '',
            ack=request.data.get('ack'),
            recipient_phone=request.data.get('recipient_phone') or '',
            recipient_name=request.data.get('recipient_name') or '',
            body=request.data.get('body') or '',
            kind=request.data.get('kind') or '',
            from_number=request.data.get('from_number') or '',
            error=request.data.get('error') or '',
            order_id=request.data.get('order_id') or None,
        )
        if message is None:
            return Response({'ok': True, 'ignored': True})
        if message.from_number:
            touch_whatsapp_session(restaurant, phone=message.from_number)
        return Response({'ok': True, 'id': message.pk, 'status': message.status})
