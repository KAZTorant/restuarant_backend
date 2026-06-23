import json
import logging
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from apps.printers.gateway.registry import complete_job
from apps.printers.models import PrintGatewayLocation

logger = logging.getLogger(__name__)


class PrintGatewayConsumer(AsyncWebsocketConsumer):
    location = None
    group_name = None

    async def connect(self):
        params = parse_qs(self.scope.get('query_string', b'').decode())
        token = params.get('token', [''])[0]
        location_id = params.get('location_id', [''])[0]

        if not token or not location_id:
            logger.warning('Print gateway rejected: missing token or location_id')
            await self.close(code=4401)
            return

        try:
            location_pk = int(location_id)
        except ValueError:
            logger.warning('Print gateway rejected: invalid location_id=%s', location_id)
            await self.close(code=4401)
            return

        location = await self._get_location(location_pk, token)
        if location is None:
            logger.warning(
                'Print gateway rejected: auth failed location_id=%s',
                location_id,
            )
            await self.close(code=4401)
            return

        self.location = location
        self.group_name = f'print_gateway_{location.pk}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self._mark_online(location, {})
        logger.info(
            'Print gateway connected location_id=%s name=%s',
            location.pk,
            location.name,
        )

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        if self.location:
            await self._mark_offline(self.location)
            logger.info(
                'Print gateway disconnected location_id=%s close_code=%s',
                self.location.pk,
                close_code,
            )

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            logger.warning('Print gateway sent invalid JSON')
            return

        msg_type = data.get('type')

        if msg_type == 'print_result':
            job_id = data.get('job_id')
            if job_id:
                complete_job(job_id, data)
            return

        if msg_type == 'heartbeat':
            printers_status = data.get('printers_status', {})
            if self.location:
                await self._update_heartbeat(self.location, printers_status)
            return

        logger.debug('Print gateway unknown message type=%s', msg_type)

    async def gateway_print_job(self, event):
        await self.send(text_data=json.dumps({
            'type': 'print_job',
            'job_id': event['job_id'],
            'payload': event['payload'],
        }))

    @staticmethod
    async def _get_location(location_id, token):
        from asgiref.sync import sync_to_async

        @sync_to_async
        def fetch():
            return PrintGatewayLocation.objects.filter(
                pk=location_id,
                token=token,
            ).first()

        return await fetch()

    @staticmethod
    async def _mark_online(location, printers_status):
        from asgiref.sync import sync_to_async

        @sync_to_async
        def update():
            location.mark_online(printers_status)

        await update()

    @staticmethod
    async def _mark_offline(location):
        from asgiref.sync import sync_to_async

        @sync_to_async
        def update():
            location.mark_offline()

        await update()

    @staticmethod
    async def _update_heartbeat(location, printers_status):
        from asgiref.sync import sync_to_async

        @sync_to_async
        def update():
            location.is_online = True
            location.last_seen_at = timezone.now()
            location.printers_status = printers_status
            location.save(update_fields=['is_online', 'last_seen_at', 'printers_status'])

        await update()
